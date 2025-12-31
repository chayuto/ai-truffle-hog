# Scanner Foundation Implementation Plan

**Date:** 2025-12-31  
**Goal:** Build comprehensive pattern-based scanner (skipping AI/ML Phase 2)

## Overview

This plan consolidates the core scanning infrastructure needed for a fully functional pattern-based secret scanner. We will implement in order of dependencies.

---

## Phase 4: FileWalker & Git Fetcher

### 4.1 FileWalker (`src/ai_truffle_hog/fetcher/file_walker.py`)

**Purpose:** Traverse local directories, enumerate files, filter by extension/path.

**Classes:**
- `FileFilter` - Configurable file filtering rules
- `FileWalker` - Directory traversal with filtering

**Key Features:**
- Configurable file extension allowlist (`.py`, `.js`, `.json`, `.yaml`, `.env`, etc.)
- Path exclusion patterns (`.git/`, `node_modules/`, `__pycache__/`, `*.min.js`)
- Binary file detection and skip
- Yield file paths as generator (memory efficient)
- Max file size limit (skip large files)

**Interface:**
```python
class FileFilter:
    include_extensions: set[str]
    exclude_patterns: list[re.Pattern]
    max_file_size_bytes: int
    skip_hidden: bool
    
    def should_include(self, path: Path) -> bool: ...

class FileWalker:
    def __init__(self, root: Path, filter: FileFilter): ...
    def walk(self) -> Iterator[Path]: ...
    def read_file(self, path: Path) -> tuple[str, int]: ...  # content, line_count
```

### 4.2 GitFetcher (`src/ai_truffle_hog/fetcher/git.py`)

**Purpose:** Clone repositories, manage temp directories, provide commit history access.

**Classes:**
- `GitFetcher` - Clone and manage repos
- `GitHistoryScanner` - Traverse commit history with PyDriller

**Key Features:**
- Clone to temp directory with auto-cleanup
- Support for HTTPS and SSH URLs
- Shallow clone option for faster scanning
- Get current HEAD commit hash
- Iterate commits with diffs using PyDriller

**Interface:**
```python
class GitFetcher:
    def __init__(self, url: str): ...
    def clone(self, shallow: bool = False) -> Path: ...
    def cleanup(self) -> None: ...
    def get_head_commit(self) -> str: ...
    
    # Context manager for auto-cleanup
    def __enter__(self) -> "GitFetcher": ...
    def __exit__(self, *args) -> None: ...

class GitHistoryScanner:
    def __init__(self, repo_path: Path): ...
    def iter_commits(self) -> Iterator[CommitInfo]: ...
    def iter_file_changes(self, commit: CommitInfo) -> Iterator[FileChange]: ...

@dataclass
class CommitInfo:
    hash: str
    author: str
    date: datetime
    message: str

@dataclass  
class FileChange:
    path: str
    content: str | None  # None if deleted
    is_added: bool
    is_deleted: bool
    is_modified: bool
```

---

## Phase 5: Scanner Core

### 5.1 PatternScanner (`src/ai_truffle_hog/core/scanner.py`)

**Purpose:** Apply provider patterns to file content, detect secrets.

**Classes:**
- `PatternScanner` - Core scanning engine
- `ScanMatch` - Individual match result

**Key Features:**
- Load all registered providers
- Run all patterns against content
- Extract line number, column, context
- Calculate entropy for each match
- Deduplicate overlapping matches
- Support scanning string content or file path

**Interface:**
```python
@dataclass
class ScanMatch:
    provider: str
    pattern_name: str
    secret_value: str
    line_number: int
    column_start: int
    column_end: int
    line_content: str
    entropy: float

class PatternScanner:
    def __init__(self, providers: list[str] | None = None): ...
    
    def scan_content(
        self, 
        content: str, 
        file_path: str = "<string>"
    ) -> list[ScanMatch]: ...
    
    def scan_file(self, file_path: Path) -> list[ScanMatch]: ...
    
    @property
    def provider_count(self) -> int: ...
    
    @property
    def pattern_count(self) -> int: ...
```

### 5.2 Context Extraction

For each match, extract:
- 3 lines before / after for context
- Variable name if detectable (simple heuristic: `var_name = "secret"`)
- File extension for categorization

---

## Phase 6: HTTP Validator

### 6.1 ValidationClient (`src/ai_truffle_hog/validator/client.py`)

**Purpose:** Async HTTP client to validate keys against provider APIs.

**Key Features:**
- Async HTTP requests with httpx
- Rate limiting per provider
- Timeout handling
- Use provider's `build_auth_header()` and `interpret_response()`
- Batch validation with concurrency limit

**Interface:**
```python
class ValidationClient:
    def __init__(
        self, 
        timeout: float = 10.0,
        max_concurrent: int = 5
    ): ...
    
    async def validate_key(
        self, 
        provider: BaseProvider, 
        key: str
    ) -> ValidationResult: ...
    
    async def validate_batch(
        self, 
        candidates: list[SecretCandidate]
    ) -> list[SecretCandidate]: ...  # Updated with validation status
    
    async def close(self) -> None: ...
    
    # Async context manager
    async def __aenter__(self) -> "ValidationClient": ...
    async def __aexit__(self, *args) -> None: ...
```

### 6.2 Rate Limiter (`src/ai_truffle_hog/validator/rate_limiter.py`)

**Already exists** - verify it works with async client.

---

## Phase 7: Reporters

### 7.1 SARIF Reporter (`src/ai_truffle_hog/reporter/sarif.py`)

**Purpose:** Generate SARIF format output for GitHub/GitLab integration.

**Key Features:**
- SARIF 2.1.0 schema compliance
- Rule definitions for each provider pattern
- Location with line/column ranges
- Code snippets in related locations
- Configurable severity levels

**Interface:**
```python
class SARIFReporter:
    def __init__(self, tool_name: str = "ai-truffle-hog"): ...
    
    def generate(
        self, 
        results: list[ScanResult]
    ) -> dict: ...  # SARIF JSON structure
    
    def write(
        self, 
        results: list[ScanResult], 
        output_path: Path
    ) -> None: ...
```

### 7.2 Console Reporter (`src/ai_truffle_hog/reporter/console.py`)

**Purpose:** Rich terminal output with tables and colors.

**Key Features:**
- Rich table for findings
- Color-coded severity
- Progress bars during scan
- Summary statistics

### 7.3 JSON Reporter (`src/ai_truffle_hog/reporter/json_reporter.py`)

**Already exists** - verify and enhance.

---

## Phase 8: Orchestrator & CLI

### 8.1 Orchestrator (`src/ai_truffle_hog/core/orchestrator.py`)

**Purpose:** Coordinate the full scan workflow.

**Workflow:**
1. Parse input (URL or file list)
2. Clone repository (if URL)
3. Walk files
4. Scan each file for patterns
5. Optionally validate discovered keys
6. Generate report

**Interface:**
```python
class ScanOrchestrator:
    def __init__(
        self,
        validate: bool = False,
        output_format: str = "table",
        providers: list[str] | None = None,
        scan_history: bool = False,
    ): ...
    
    async def scan_repo(self, url: str) -> ScanResult: ...
    async def scan_local(self, path: Path) -> ScanResult: ...
    async def scan_batch(self, urls: list[str]) -> list[ScanResult]: ...
```

### 8.2 CLI Implementation (`src/ai_truffle_hog/cli/app.py`)

**Update scan command to:**
- Parse target (URL vs file vs local path)
- Initialize orchestrator with options
- Run scan
- Display results with chosen reporter

**Additional commands:**
- `aitruffle providers` - List registered providers
- `aitruffle validate <key>` - Validate a single key

---

## Implementation Order

```
Phase 4.1: FileWalker        ──┐
Phase 4.2: GitFetcher        ──┼──> Phase 5: Scanner ──> Phase 6: Validator
                               │
Phase 7.1: SARIF Reporter    ──┤
Phase 7.2: Console Reporter  ──┘
                                       │
                                       ▼
                              Phase 8: Orchestrator + CLI
```

---

## Test Coverage Requirements

Each phase must include:
1. Unit tests for all classes
2. Integration tests for workflows
3. Edge cases (empty files, binary files, huge files)
4. Mock tests for external dependencies (Git, HTTP)

---

## Dependencies to Add

```toml
# pyproject.toml additions
pydriller = "^2.6"    # Git history mining
rich = "^13.0"        # Console output
```

---

## Files to Create/Modify

| File | Action | Phase |
|------|--------|-------|
| `src/ai_truffle_hog/fetcher/file_walker.py` | Implement | 4.1 |
| `src/ai_truffle_hog/fetcher/git.py` | Implement | 4.2 |
| `src/ai_truffle_hog/core/scanner.py` | Implement | 5 |
| `src/ai_truffle_hog/validator/client.py` | Implement | 6 |
| `src/ai_truffle_hog/reporter/sarif.py` | Create | 7.1 |
| `src/ai_truffle_hog/reporter/console.py` | Implement | 7.2 |
| `src/ai_truffle_hog/core/orchestrator.py` | Implement | 8 |
| `src/ai_truffle_hog/cli/app.py` | Update | 8 |
| `tests/unit/test_file_walker.py` | Create | 4.1 |
| `tests/unit/test_git_fetcher.py` | Create | 4.2 |
| `tests/unit/test_scanner.py` | Create | 5 |
| `tests/unit/test_validator_client.py` | Create | 6 |
| `tests/unit/test_sarif_reporter.py` | Create | 7.1 |
| `tests/integration/test_scan_workflow.py` | Create | 8 |

---

## Success Criteria

- [ ] Can scan local directory for secrets
- [ ] Can clone and scan GitHub repository
- [ ] Can scan git history for deleted secrets
- [ ] Can validate discovered keys (optional flag)
- [ ] Outputs SARIF, JSON, and table formats
- [ ] All tests pass, ruff clean, mypy clean
- [ ] CLI fully functional with `aitruffle scan <target>`
