# AI-Truffle-Hog: Coding Agent Task Breakdown

**Document Version:** 1.0  
**Date:** 2025-12-31  
**Author:** Architecture Analysis  
**Status:** Implementation Tasks

---

## Overview

This document breaks down the AI-Truffle-Hog implementation into discrete, executable tasks for a coding agent. Each task is self-contained with clear inputs, outputs, acceptance criteria, and dependencies.

**Execution Strategy:** Tasks are organized into phases. Within each phase, tasks can be executed in order. Some tasks can be parallelized.

---

## Phase 1: Project Foundation

### Task 1.1: Initialize Project Structure

**Objective:** Create the basic Python project skeleton with all directories.

**Input:** None (greenfield)

**Actions:**
1. Create the `src/ai_truffle_hog/` directory structure
2. Create all `__init__.py` files
3. Create empty placeholder files for all modules
4. Create `tests/` directory structure with `conftest.py`
5. Create `scripts/` directory

**Output Files:**
```
src/ai_truffle_hog/__init__.py
src/ai_truffle_hog/__main__.py
src/ai_truffle_hog/cli/__init__.py
src/ai_truffle_hog/cli/app.py
src/ai_truffle_hog/cli/commands/__init__.py
src/ai_truffle_hog/cli/commands/scan.py
src/ai_truffle_hog/core/__init__.py
src/ai_truffle_hog/core/models.py
src/ai_truffle_hog/core/scanner.py
src/ai_truffle_hog/core/orchestrator.py
src/ai_truffle_hog/providers/__init__.py
src/ai_truffle_hog/providers/base.py
src/ai_truffle_hog/providers/registry.py
src/ai_truffle_hog/fetcher/__init__.py
src/ai_truffle_hog/fetcher/git.py
src/ai_truffle_hog/fetcher/file_walker.py
src/ai_truffle_hog/validator/__init__.py
src/ai_truffle_hog/validator/client.py
src/ai_truffle_hog/validator/rate_limiter.py
src/ai_truffle_hog/reporter/__init__.py
src/ai_truffle_hog/reporter/console.py
src/ai_truffle_hog/reporter/json_reporter.py
src/ai_truffle_hog/reporter/log_handler.py
src/ai_truffle_hog/utils/__init__.py
src/ai_truffle_hog/utils/config.py
src/ai_truffle_hog/utils/redaction.py
src/ai_truffle_hog/utils/entropy.py
tests/__init__.py
tests/conftest.py
tests/unit/__init__.py
tests/integration/__init__.py
tests/e2e/__init__.py
scripts/dev_setup.sh
```

**Acceptance Criteria:**
- All directories exist
- All `__init__.py` files exist (can be empty or have basic exports)
- `__main__.py` has minimal entry point stub

**Dependencies:** None

---

### Task 1.2: Create Project Configuration Files

**Objective:** Set up pyproject.toml and all project configuration files.

**Input:** Specifications from `20251231_project_setup_spec.md`

**Actions:**
1. Create `pyproject.toml` with all dependencies and tool configurations
2. Create `.gitignore` with comprehensive Python ignores
3. Create `.pre-commit-config.yaml`
4. Create `.python-version` (content: `3.11`)
5. Create `.env.example`
6. Create `.vscode/settings.json`
7. Update `README.md` with project overview

**Output Files:**
```
pyproject.toml
.gitignore
.pre-commit-config.yaml
.python-version
.env.example
.vscode/settings.json
README.md (update)
```

**Acceptance Criteria:**
- `pip install -e ".[dev]"` succeeds
- `ruff check .` runs without configuration errors
- `mypy src/` runs without configuration errors
- `pytest` runs (even if no tests pass yet)

**Dependencies:** Task 1.1

---

### Task 1.3: Create Development Setup Script

**Objective:** Create a shell script that automates development environment setup.

**Input:** Specifications from `20251231_project_setup_spec.md`

**Actions:**
1. Create `scripts/dev_setup.sh` with:
   - Python version check
   - Virtual environment creation
   - Dependency installation
   - Pre-commit hook installation
   - .env file creation

**Output Files:**
```
scripts/dev_setup.sh (executable)
```

**Acceptance Criteria:**
- Script is executable (`chmod +x`)
- Script creates venv in `.venv/`
- Script installs all dependencies
- Script installs pre-commit hooks

**Dependencies:** Task 1.2

---

### Task 1.4: Create GitHub Actions CI

**Objective:** Set up continuous integration workflow.

**Input:** Specifications from `20251231_project_setup_spec.md`

**Actions:**
1. Create `.github/workflows/ci.yml` with:
   - Lint job (ruff)
   - Type check job (mypy)
   - Test job (pytest on Python 3.11, 3.12, 3.13)

**Output Files:**
```
.github/workflows/ci.yml
```

**Acceptance Criteria:**
- Workflow syntax is valid
- Jobs run in parallel where possible

**Dependencies:** Task 1.2

---

## Phase 2: Core Models and Utilities

### Task 2.1: Implement Data Models

**Objective:** Create Pydantic models for all core data structures.

**Input:** Specifications from `20251231_architecture_analysis.md`

**Actions:**
1. Implement `SecretCandidate` model
2. Implement `ScanResult` model
3. Implement `ValidationResult` model
4. Implement `ScanSession` model
5. Implement configuration models

**Output Files:**
```
src/ai_truffle_hog/core/models.py
```

**Code Specification:**

```python
"""Core data models for AI Truffle Hog."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Status of key validation."""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    SKIPPED = "skipped"


class SecretCandidate(BaseModel):
    """A potential secret found during scanning."""
    
    id: UUID = Field(default_factory=uuid4)
    provider: str
    secret_value: str
    file_path: str
    line_number: int
    column_start: int
    column_end: int
    context_before: str = ""
    context_after: str = ""
    variable_name: Optional[str] = None
    pattern_name: str = ""
    entropy_score: float = 0.0
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_timestamp: Optional[datetime] = None
    validation_message: Optional[str] = None
    validation_metadata: Optional[dict] = None


class ScanResult(BaseModel):
    """Result of scanning a single repository."""
    
    repo_url: str
    repo_path: Optional[str] = None
    commit_hash: Optional[str] = None
    scan_started_at: datetime
    scan_completed_at: Optional[datetime] = None
    files_scanned: int = 0
    secrets_found: list[SecretCandidate] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        if self.scan_completed_at and self.scan_started_at:
            return (self.scan_completed_at - self.scan_started_at).total_seconds()
        return 0.0


class ScanSession(BaseModel):
    """A complete scanning session (may include multiple repos)."""
    
    session_id: UUID = Field(default_factory=uuid4)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    targets: list[str] = Field(default_factory=list)
    results: list[ScanResult] = Field(default_factory=list)
    validate_keys: bool = False
    
    @property
    def total_secrets_found(self) -> int:
        return sum(len(r.secrets_found) for r in self.results)
```

**Acceptance Criteria:**
- All models validate correctly
- Models serialize to JSON
- Unit tests pass for model validation

**Dependencies:** Task 1.1

---

### Task 2.2: Implement Entropy Calculation

**Objective:** Create Shannon entropy calculation utility.

**Input:** Research documents reference entropy thresholds of 4.5

**Actions:**
1. Implement Shannon entropy calculation
2. Add character set detection (alphanumeric, hex, base64)
3. Add tests

**Output Files:**
```
src/ai_truffle_hog/utils/entropy.py
tests/unit/test_entropy.py
```

**Code Specification:**

```python
"""Shannon entropy calculation for secret detection."""

import math
from collections import Counter


def calculate_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of a string.
    
    Higher entropy indicates more randomness (likely a secret).
    Typical thresholds:
    - < 3.0: Low entropy (common words)
    - 3.0-4.0: Medium entropy (mixed content)
    - 4.0-5.0: High entropy (potential secrets)
    - > 5.0: Very high entropy (likely cryptographic)
    
    Args:
        text: The string to analyze
        
    Returns:
        Entropy value in bits per character
    """
    if not text:
        return 0.0
    
    # Count character frequencies
    freq = Counter(text)
    length = len(text)
    
    # Calculate entropy: -Σ p(x) * log2(p(x))
    entropy = 0.0
    for count in freq.values():
        probability = count / length
        entropy -= probability * math.log2(probability)
    
    return entropy


def is_high_entropy(text: str, threshold: float = 4.5) -> bool:
    """Check if text has high entropy (likely a secret)."""
    return calculate_entropy(text) >= threshold


def detect_charset(text: str) -> str:
    """
    Detect the character set of a string.
    
    Returns:
        One of: 'hex', 'base64', 'alphanumeric', 'mixed'
    """
    if not text:
        return "empty"
    
    hex_chars = set("0123456789abcdefABCDEF")
    base64_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
    alphanum_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
    
    text_chars = set(text)
    
    if text_chars <= hex_chars:
        return "hex"
    elif text_chars <= base64_chars:
        return "base64"
    elif text_chars <= alphanum_chars:
        return "alphanumeric"
    else:
        return "mixed"
```

**Acceptance Criteria:**
- Entropy calculation is accurate (test with known values)
- Low entropy strings (e.g., "aaaaaaa") return < 1.0
- High entropy strings (random) return > 4.0
- Tests cover edge cases (empty string, single char, etc.)

**Dependencies:** Task 1.1

---

### Task 2.3: Implement Secret Redaction

**Objective:** Create utility for safely redacting secrets in logs and output.

**Input:** Research documents specify showing first 8 + last 4 chars

**Actions:**
1. Implement redaction function with configurable format
2. Add tests

**Output Files:**
```
src/ai_truffle_hog/utils/redaction.py
tests/unit/test_redaction.py
```

**Code Specification:**

```python
"""Secret redaction utilities for safe logging."""

from typing import Optional


def redact_secret(
    secret: str,
    show_prefix: int = 8,
    show_suffix: int = 4,
    mask_char: str = "*",
    min_length_to_redact: int = 12,
) -> str:
    """
    Redact a secret for safe display.
    
    Args:
        secret: The secret to redact
        show_prefix: Number of characters to show at start
        show_suffix: Number of characters to show at end
        mask_char: Character to use for masking
        min_length_to_redact: Secrets shorter than this are fully masked
        
    Returns:
        Redacted string like "sk-proj-****...****xyz9"
    """
    if not secret:
        return ""
    
    length = len(secret)
    
    # Fully mask short secrets
    if length < min_length_to_redact:
        return mask_char * length
    
    # Adjust if secret is too short for prefix+suffix
    if show_prefix + show_suffix >= length:
        show_prefix = length // 3
        show_suffix = length // 3
    
    prefix = secret[:show_prefix]
    suffix = secret[-show_suffix:] if show_suffix > 0 else ""
    masked_length = length - show_prefix - show_suffix
    
    return f"{prefix}{mask_char * 4}...{mask_char * 4}{suffix}"


def redact_in_text(
    text: str,
    secret: str,
    replacement: Optional[str] = None,
) -> str:
    """
    Replace occurrences of a secret in text with redacted version.
    
    Args:
        text: Text that may contain the secret
        secret: The secret to redact
        replacement: Custom replacement (default: auto-redact)
        
    Returns:
        Text with secret redacted
    """
    if not secret or not text:
        return text
    
    if replacement is None:
        replacement = redact_secret(secret)
    
    return text.replace(secret, replacement)
```

**Acceptance Criteria:**
- Redaction preserves identifiable prefix for debugging
- Short secrets are fully masked
- Empty inputs handled gracefully
- Tests verify redaction format

**Dependencies:** Task 1.1

---

### Task 2.4: Implement Configuration System

**Objective:** Create configuration management with environment variables and file support.

**Input:** Specifications from architecture analysis

**Actions:**
1. Create Pydantic Settings model
2. Support environment variables (ATH_ prefix)
3. Support TOML configuration files
4. Create default configuration

**Output Files:**
```
src/ai_truffle_hog/utils/config.py
src/ai_truffle_hog/config/default.toml
tests/unit/test_config.py
```

**Code Specification:**

```python
"""Configuration management for AI Truffle Hog."""

import tomllib
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScannerSettings(BaseSettings):
    """Scanner configuration."""
    
    file_extensions: list[str] = Field(
        default=[".py", ".js", ".ts", ".env", ".json", ".yaml", ".yml", 
                 ".toml", ".xml", ".properties", ".conf", ".go", ".rb", ".php"]
    )
    max_file_size_kb: int = 1024
    skip_paths: list[str] = Field(
        default=["node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"]
    )
    entropy_threshold: float = 4.5


class ValidatorSettings(BaseSettings):
    """Validator configuration."""
    
    enabled: bool = True
    timeout_seconds: int = 10
    max_concurrent: int = 5
    retry_count: int = 3
    retry_delay_seconds: float = 1.0


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    
    level: str = "INFO"
    format: str = "json"  # "json" or "console"
    file: Optional[str] = None
    redact_secrets: bool = True


class OutputSettings(BaseSettings):
    """Output configuration."""
    
    format: str = "table"  # "table" or "json"
    show_context: bool = True
    context_lines: int = 3


class Settings(BaseSettings):
    """Main settings container."""
    
    model_config = SettingsConfigDict(
        env_prefix="ATH_",
        env_nested_delimiter="__",
        extra="ignore",
    )
    
    scanner: ScannerSettings = Field(default_factory=ScannerSettings)
    validator: ValidatorSettings = Field(default_factory=ValidatorSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    output: OutputSettings = Field(default_factory=OutputSettings)


def load_config(config_path: Optional[Path] = None) -> Settings:
    """
    Load configuration from file and environment.
    
    Priority (highest to lowest):
    1. Environment variables
    2. Config file
    3. Defaults
    """
    config_data = {}
    
    if config_path and config_path.exists():
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)
    
    return Settings(**config_data)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings
```

**Acceptance Criteria:**
- Settings load from defaults
- Environment variables override defaults
- TOML files override defaults
- Nested settings work (ATH_SCANNER__MAX_FILE_SIZE_KB)

**Dependencies:** Task 1.1

---

## Phase 3: Provider Implementation

### Task 3.1: Implement Base Provider

**Objective:** Create abstract base class for all providers.

**Input:** Specifications from `20251231_provider_specification.md`

**Actions:**
1. Create abstract base class with all required methods
2. Create ValidationStatus enum
3. Create ValidationResult dataclass

**Output Files:**
```
src/ai_truffle_hog/providers/base.py
```

**Code:** See `20251231_provider_specification.md` Section 2

**Acceptance Criteria:**
- Abstract methods are properly defined
- ValidationStatus enum has all states
- ValidationResult holds all needed data

**Dependencies:** Task 2.1

---

### Task 3.2: Implement OpenAI Provider

**Objective:** Implement OpenAI secret detection and validation.

**Input:** Specifications from `20251231_provider_specification.md` Section 3

**Actions:**
1. Implement OpenAIProvider class
2. Add regex patterns for sk-, sk-proj-, sk-org-, sk-admin-
3. Implement validation against /v1/models
4. Add unit tests

**Output Files:**
```
src/ai_truffle_hog/providers/openai.py
tests/unit/test_providers/test_openai.py
```

**Acceptance Criteria:**
- Matches valid OpenAI key formats
- Does not match non-OpenAI strings
- Validation interprets all response codes correctly
- Tests cover pattern matching and response interpretation

**Dependencies:** Task 3.1

---

### Task 3.3: Implement Anthropic Provider

**Objective:** Implement Anthropic secret detection and validation.

**Input:** Specifications from `20251231_provider_specification.md` Section 4

**Actions:**
1. Implement AnthropicProvider class
2. Add regex patterns for sk-ant-api03-
3. Implement validation against /v1/messages (POST, minimal body)
4. Handle x-api-key header and anthropic-version header
5. Add unit tests

**Output Files:**
```
src/ai_truffle_hog/providers/anthropic.py
tests/unit/test_providers/test_anthropic.py
```

**Acceptance Criteria:**
- Matches valid Anthropic key formats
- Includes anthropic-version header in validation
- Handles credit balance errors as QUOTA_EXCEEDED
- Tests cover pattern matching and response interpretation

**Dependencies:** Task 3.1

---

### Task 3.4: Implement Hugging Face Provider

**Objective:** Implement Hugging Face secret detection and validation.

**Input:** Specifications from `20251231_provider_specification.md` Section 5

**Actions:**
1. Implement HuggingFaceProvider class
2. Add regex pattern for hf_
3. Implement validation against /api/whoami-v2
4. Extract user metadata from response
5. Add unit tests

**Output Files:**
```
src/ai_truffle_hog/providers/huggingface.py
tests/unit/test_providers/test_huggingface.py
```

**Acceptance Criteria:**
- Matches valid HF token format (hf_ + 34 chars)
- Validation extracts username and scopes
- Tests cover pattern matching and response interpretation

**Dependencies:** Task 3.1

---

### Task 3.5: Implement Remaining Providers

**Objective:** Implement Cohere, Replicate, Google Gemini, Groq, LangSmith providers.

**Input:** Specifications from `20251231_provider_specification.md` Sections 6-10

**Actions:**
1. Implement CohereProvider (contextual patterns, /v1/check-api-key)
2. Implement ReplicateProvider (r8_ prefix, /v1/account)
3. Implement GoogleGeminiProvider (AIza prefix, query param auth)
4. Implement GroqProvider (gsk_ prefix, OpenAI-compatible)
5. Implement LangSmithProvider (lsv2_ prefix, x-api-key header)
6. Add unit tests for each

**Output Files:**
```
src/ai_truffle_hog/providers/cohere.py
src/ai_truffle_hog/providers/replicate.py
src/ai_truffle_hog/providers/google.py
src/ai_truffle_hog/providers/groq.py
src/ai_truffle_hog/providers/langsmith.py
tests/unit/test_providers/test_cohere.py
tests/unit/test_providers/test_replicate.py
tests/unit/test_providers/test_google.py
tests/unit/test_providers/test_groq.py
tests/unit/test_providers/test_langsmith.py
```

**Acceptance Criteria:**
- All providers match their expected patterns
- Google provider uses query parameter authentication
- LangSmith provider uses x-api-key header
- Tests cover each provider

**Dependencies:** Task 3.1

---

### Task 3.6: Implement Provider Registry

**Objective:** Create registry to manage all providers.

**Input:** Specifications from `20251231_provider_specification.md` Section 11

**Actions:**
1. Implement ProviderRegistry class
2. Create initialization function
3. Export from providers/__init__.py

**Output Files:**
```
src/ai_truffle_hog/providers/registry.py
src/ai_truffle_hog/providers/__init__.py (update)
```

**Acceptance Criteria:**
- Registry initializes all providers
- Can retrieve provider by name
- Can iterate all providers
- Providers are singletons

**Dependencies:** Tasks 3.2-3.5

---

## Phase 4: Fetcher Implementation

### Task 4.1: Implement Git Fetcher

**Objective:** Create Git repository cloning and management.

**Input:** Architecture analysis specifications

**Actions:**
1. Implement clone_repository function (shallow clone)
2. Implement get_head_commit function
3. Implement cleanup function
4. Handle clone errors gracefully
5. Add integration tests

**Output Files:**
```
src/ai_truffle_hog/fetcher/git.py
tests/integration/test_git.py
```

**Code Specification:**

```python
"""Git repository operations."""

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from git import Repo, GitCommandError


class GitFetcher:
    """Handles Git repository cloning and management."""
    
    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "ai-truffle-hog"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def clone(
        self, 
        repo_url: str, 
        depth: int = 1,
    ) -> tuple[Path, str]:
        """
        Clone a repository.
        
        Args:
            repo_url: Git repository URL
            depth: Clone depth (1 for shallow)
            
        Returns:
            Tuple of (repo_path, commit_hash)
            
        Raises:
            GitCloneError: If clone fails
        """
        # Generate unique temp directory
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        clone_path = self.temp_dir / f"{repo_name}_{uuid4().hex[:8]}"
        
        try:
            repo = Repo.clone_from(
                repo_url,
                clone_path,
                depth=depth,
                single_branch=True,
            )
            commit_hash = repo.head.commit.hexsha
            return clone_path, commit_hash
            
        except GitCommandError as e:
            raise GitCloneError(f"Failed to clone {repo_url}: {e}") from e
    
    def cleanup(self, repo_path: Path) -> None:
        """Remove a cloned repository."""
        if repo_path.exists():
            shutil.rmtree(repo_path, ignore_errors=True)
    
    def cleanup_all(self) -> None:
        """Remove all temporary repositories."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class GitCloneError(Exception):
    """Raised when git clone fails."""
    pass
```

**Acceptance Criteria:**
- Clones public GitHub repositories
- Returns commit hash of HEAD
- Cleanup removes temp directory
- Handles invalid URLs gracefully
- Integration tests use real small public repo

**Dependencies:** Task 1.2

---

### Task 4.2: Implement File Walker

**Objective:** Enumerate and filter files for scanning.

**Input:** Configuration specifications for file extensions and skip paths

**Actions:**
1. Implement file enumeration with filtering
2. Support extension allowlist
3. Support path blocklist
4. Handle binary file detection
5. Add tests

**Output Files:**
```
src/ai_truffle_hog/fetcher/file_walker.py
tests/unit/test_file_walker.py
```

**Code Specification:**

```python
"""File enumeration and filtering for scanning."""

from pathlib import Path
from typing import Iterator

from ai_truffle_hog.utils.config import get_settings


class FileWalker:
    """Walks directories and yields scannable files."""
    
    def __init__(
        self,
        extensions: list[str] | None = None,
        skip_paths: list[str] | None = None,
        max_file_size_kb: int | None = None,
    ):
        settings = get_settings()
        self.extensions = set(extensions or settings.scanner.file_extensions)
        self.skip_paths = set(skip_paths or settings.scanner.skip_paths)
        self.max_file_size = (max_file_size_kb or settings.scanner.max_file_size_kb) * 1024
    
    def walk(self, root: Path) -> Iterator[Path]:
        """
        Yield all scannable files under root.
        
        Filters:
        - Extension must be in allowlist
        - Path must not contain blocklisted directories
        - File size must be under limit
        """
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Check skip paths
            if self._should_skip(file_path):
                continue
            
            # Check extension
            if file_path.suffix.lower() not in self.extensions:
                continue
            
            # Check file size
            try:
                if file_path.stat().st_size > self.max_file_size:
                    continue
            except OSError:
                continue
            
            yield file_path
    
    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        parts = path.parts
        return any(skip in parts for skip in self.skip_paths)
    
    def read_file(self, path: Path) -> str | None:
        """
        Read file contents safely.
        
        Returns None if file cannot be read (binary, encoding error).
        """
        try:
            return path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return None
```

**Acceptance Criteria:**
- Correctly filters by extension
- Skips blocklisted directories
- Skips large files
- Handles read errors gracefully
- Tests verify filtering logic

**Dependencies:** Task 2.4

---

## Phase 5: Scanner Implementation

### Task 5.1: Implement Pattern Scanner

**Objective:** Create the core pattern matching engine.

**Input:** Provider patterns from registry

**Actions:**
1. Implement Scanner class that uses all providers
2. Extract context around matches
3. Calculate entropy for matches
4. Generate SecretCandidate objects
5. Add tests

**Output Files:**
```
src/ai_truffle_hog/core/scanner.py
tests/unit/test_scanner.py
```

**Code Specification:**

```python
"""Pattern scanning engine."""

import re
from pathlib import Path
from typing import Iterator

from ai_truffle_hog.core.models import SecretCandidate
from ai_truffle_hog.providers.registry import ProviderRegistry
from ai_truffle_hog.utils.entropy import calculate_entropy


class Scanner:
    """Scans text for secret patterns."""
    
    def __init__(self, context_lines: int = 3):
        self.context_lines = context_lines
        self.registry = ProviderRegistry()
    
    def scan_text(
        self, 
        text: str, 
        file_path: str = "<unknown>",
    ) -> Iterator[SecretCandidate]:
        """
        Scan text for secrets.
        
        Yields SecretCandidate for each match.
        """
        lines = text.splitlines(keepends=True)
        
        for provider in self.registry.all():
            for pattern in provider.patterns:
                for match in pattern.finditer(text):
                    secret = match.group(1)
                    
                    # Calculate position
                    line_num, col_start = self._get_position(text, match.start())
                    _, col_end = self._get_position(text, match.end())
                    
                    # Extract context
                    context_before, context_after = self._get_context(
                        lines, line_num
                    )
                    
                    # Extract variable name if present
                    var_name = self._extract_variable_name(text, match.start())
                    
                    yield SecretCandidate(
                        provider=provider.name,
                        secret_value=secret,
                        file_path=file_path,
                        line_number=line_num,
                        column_start=col_start,
                        column_end=col_end,
                        context_before=context_before,
                        context_after=context_after,
                        variable_name=var_name,
                        pattern_name=pattern.pattern,
                        entropy_score=calculate_entropy(secret),
                    )
    
    def scan_file(self, file_path: Path) -> Iterator[SecretCandidate]:
        """Scan a file for secrets."""
        try:
            text = file_path.read_text(encoding="utf-8")
            yield from self.scan_text(text, str(file_path))
        except (UnicodeDecodeError, OSError):
            pass  # Skip unreadable files
    
    def _get_position(self, text: str, char_pos: int) -> tuple[int, int]:
        """Convert character position to (line, column)."""
        line = text.count("\n", 0, char_pos) + 1
        last_newline = text.rfind("\n", 0, char_pos)
        col = char_pos - last_newline
        return line, col
    
    def _get_context(
        self, 
        lines: list[str], 
        line_num: int,
    ) -> tuple[str, str]:
        """Extract context lines before and after."""
        start = max(0, line_num - self.context_lines - 1)
        end = min(len(lines), line_num + self.context_lines)
        
        before = "".join(lines[start:line_num - 1])
        after = "".join(lines[line_num:end])
        
        return before.strip(), after.strip()
    
    def _extract_variable_name(
        self, 
        text: str, 
        match_start: int,
    ) -> str | None:
        """Try to extract variable name before the match."""
        # Look backwards for assignment pattern
        prefix = text[max(0, match_start - 100):match_start]
        
        # Match patterns like: VAR_NAME = " or var_name: "
        patterns = [
            r'([A-Z_][A-Z0-9_]*)\s*=\s*[\'"]?\s*$',  # UPPER_CASE =
            r'([a-z_][a-z0-9_]*)\s*=\s*[\'"]?\s*$',  # lower_case =
            r'"([^"]+)"\s*:\s*[\'"]?\s*$',           # "json_key":
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prefix, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
```

**Acceptance Criteria:**
- Finds all secrets from all providers
- Extracts correct line numbers
- Extracts context correctly
- Calculates entropy for each match
- Tests verify scanning accuracy

**Dependencies:** Tasks 3.6, 2.1, 2.2

---

## Phase 6: Validator Implementation

### Task 6.1: Implement Async Validation Client

**Objective:** Create async HTTP client for key validation.

**Input:** Provider validation specifications

**Actions:**
1. Implement async validation using httpx
2. Handle timeouts and retries
3. Support rate limiting
4. Parse provider responses
5. Add tests with mocking

**Output Files:**
```
src/ai_truffle_hog/validator/client.py
tests/unit/test_validator.py
```

**Code Specification:**

```python
"""Async validation client for API keys."""

import asyncio
from typing import Sequence

import httpx

from ai_truffle_hog.core.models import SecretCandidate, ValidationStatus
from ai_truffle_hog.providers.base import BaseProvider, ValidationResult
from ai_truffle_hog.providers.registry import ProviderRegistry
from ai_truffle_hog.utils.config import get_settings


class ValidationClient:
    """Async client for validating API keys."""
    
    def __init__(
        self,
        timeout: float | None = None,
        max_concurrent: int | None = None,
    ):
        settings = get_settings()
        self.timeout = timeout or settings.validator.timeout_seconds
        self.max_concurrent = max_concurrent or settings.validator.max_concurrent
        self.registry = ProviderRegistry()
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
    
    async def validate(
        self, 
        candidate: SecretCandidate,
    ) -> SecretCandidate:
        """Validate a single candidate."""
        provider = self.registry.get(candidate.provider)
        if not provider:
            candidate.validation_status = ValidationStatus.SKIPPED
            candidate.validation_message = f"Unknown provider: {candidate.provider}"
            return candidate
        
        async with self._semaphore:
            result = await self._validate_with_provider(
                candidate.secret_value, 
                provider,
            )
        
        candidate.validation_status = result.status
        candidate.validation_message = result.message
        candidate.validation_metadata = result.metadata
        
        return candidate
    
    async def validate_batch(
        self, 
        candidates: Sequence[SecretCandidate],
    ) -> list[SecretCandidate]:
        """Validate multiple candidates concurrently."""
        tasks = [self.validate(c) for c in candidates]
        return await asyncio.gather(*tasks)
    
    async def _validate_with_provider(
        self,
        key: str,
        provider: BaseProvider,
    ) -> ValidationResult:
        """Perform validation against provider API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = provider.build_auth_header(key)
                
                # Handle providers with different auth methods
                if hasattr(provider, "build_validation_url"):
                    url = provider.build_validation_url(key)
                    response = await client.get(url)
                elif hasattr(provider, "get_validation_body"):
                    response = await client.post(
                        provider.validation_endpoint,
                        headers=headers,
                        json=provider.get_validation_body(),
                    )
                else:
                    response = await client.get(
                        provider.validation_endpoint,
                        headers=headers,
                    )
                
                try:
                    body = response.json()
                except Exception:
                    body = None
                
                return provider.interpret_response(response.status_code, body)
                
        except httpx.TimeoutException:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message="Validation request timed out",
            )
        except httpx.RequestError as e:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=f"Network error: {e}",
            )
```

**Acceptance Criteria:**
- Validates keys asynchronously
- Respects concurrency limits
- Handles timeouts gracefully
- Tests use mocked HTTP responses

**Dependencies:** Task 3.6, Task 2.1

---

### Task 6.2: Implement Rate Limiter

**Objective:** Create rate limiting for validation requests.

**Input:** Provider rate limits

**Actions:**
1. Implement token bucket rate limiter
2. Support per-provider limits
3. Add tests

**Output Files:**
```
src/ai_truffle_hog/validator/rate_limiter.py
tests/unit/test_rate_limiter.py
```

**Acceptance Criteria:**
- Limits request rate correctly
- Handles burst traffic
- Tests verify rate limiting behavior

**Dependencies:** Task 1.1

---

## Phase 7: Reporter Implementation

### Task 7.1: Implement Console Reporter

**Objective:** Create rich console output for scan results.

**Input:** Output specifications

**Actions:**
1. Use Rich library for tables and formatting
2. Show progress during scanning
3. Display results in formatted table
4. Support different verbosity levels
5. Redact secrets in output

**Output Files:**
```
src/ai_truffle_hog/reporter/console.py
```

**Acceptance Criteria:**
- Displays results in readable table
- Shows progress indicators
- Redacts secrets by default
- Supports color/no-color modes

**Dependencies:** Task 2.3

---

### Task 7.2: Implement JSON Reporter

**Objective:** Create JSON file output for scan results.

**Input:** Output specifications

**Actions:**
1. Serialize ScanSession to JSON
2. Support pretty-printing
3. Support redaction option
4. Handle file writing

**Output Files:**
```
src/ai_truffle_hog/reporter/json_reporter.py
```

**Acceptance Criteria:**
- Generates valid JSON
- Includes all scan metadata
- Supports redaction option

**Dependencies:** Task 2.1

---

### Task 7.3: Implement Logging Handler

**Objective:** Set up structured logging with structlog.

**Input:** Logging specifications from architecture

**Actions:**
1. Configure structlog for JSON output
2. Support console and file logging
3. Implement secret redaction processor
4. Add log levels configuration

**Output Files:**
```
src/ai_truffle_hog/reporter/log_handler.py
```

**Acceptance Criteria:**
- Logs in JSON format
- Includes all required fields (timestamp, level, component, etc.)
- Redacts secrets before writing
- Configurable via settings

**Dependencies:** Task 2.3, Task 2.4

---

## Phase 8: Orchestrator and CLI

### Task 8.1: Implement Scan Orchestrator

**Objective:** Create the main orchestration logic that ties all components together.

**Input:** Architecture analysis

**Actions:**
1. Implement Orchestrator class
2. Handle single repo vs file list input
3. Coordinate fetch -> scan -> validate -> report flow
4. Manage cleanup
5. Add integration tests

**Output Files:**
```
src/ai_truffle_hog/core/orchestrator.py
tests/integration/test_orchestrator.py
```

**Code Specification:**

```python
"""Scan orchestration."""

from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

from ai_truffle_hog.core.models import ScanResult, ScanSession, SecretCandidate
from ai_truffle_hog.core.scanner import Scanner
from ai_truffle_hog.fetcher.git import GitFetcher, GitCloneError
from ai_truffle_hog.fetcher.file_walker import FileWalker
from ai_truffle_hog.validator.client import ValidationClient
from ai_truffle_hog.utils.config import get_settings


class Orchestrator:
    """Orchestrates the complete scan workflow."""
    
    def __init__(
        self,
        validate: bool = False,
        callback: callable | None = None,
    ):
        self.validate = validate
        self.callback = callback
        self.git = GitFetcher()
        self.walker = FileWalker()
        self.scanner = Scanner()
        self.validator = ValidationClient() if validate else None
    
    async def scan_url(self, repo_url: str) -> ScanResult:
        """Scan a single repository URL."""
        result = ScanResult(
            repo_url=repo_url,
            scan_started_at=datetime.utcnow(),
        )
        
        try:
            # Clone
            repo_path, commit_hash = self.git.clone(repo_url)
            result.repo_path = str(repo_path)
            result.commit_hash = commit_hash
            
            # Scan
            candidates = []
            for file_path in self.walker.walk(repo_path):
                result.files_scanned += 1
                for candidate in self.scanner.scan_file(file_path):
                    candidates.append(candidate)
                    if self.callback:
                        self.callback("secret_found", candidate)
            
            # Validate
            if self.validate and candidates and self.validator:
                candidates = await self.validator.validate_batch(candidates)
            
            result.secrets_found = candidates
            
        except GitCloneError as e:
            result.errors.append(str(e))
        finally:
            # Cleanup
            if result.repo_path:
                self.git.cleanup(Path(result.repo_path))
        
        result.scan_completed_at = datetime.utcnow()
        return result
    
    async def scan_file(self, file_path: Path) -> list[ScanResult]:
        """Scan multiple repos from a file."""
        results = []
        with open(file_path) as f:
            urls = [line.strip() for line in f if line.strip()]
        
        for url in urls:
            result = await self.scan_url(url)
            results.append(result)
        
        return results
    
    async def run(self, target: str) -> ScanSession:
        """Run a complete scan session."""
        session = ScanSession(validate_keys=self.validate)
        
        target_path = Path(target)
        
        if target_path.exists() and target_path.is_file():
            session.targets = [target]
            session.results = await self.scan_file(target_path)
        else:
            session.targets = [target]
            result = await self.scan_url(target)
            session.results = [result]
        
        session.completed_at = datetime.utcnow()
        return session
```

**Acceptance Criteria:**
- Handles single URL input
- Handles file with list of URLs
- Coordinates all components
- Handles errors gracefully
- Cleans up temporary files

**Dependencies:** Tasks 4.1, 4.2, 5.1, 6.1

---

### Task 8.2: Implement CLI Application

**Objective:** Create the Typer CLI application.

**Input:** CLI specifications

**Actions:**
1. Create main Typer app
2. Implement scan command with all options
3. Add version command
4. Wire up to orchestrator
5. Add help documentation

**Output Files:**
```
src/ai_truffle_hog/cli/app.py
src/ai_truffle_hog/cli/commands/scan.py
src/ai_truffle_hog/__main__.py
```

**Code Specification:**

```python
# src/ai_truffle_hog/cli/app.py
"""CLI application."""

import typer

from ai_truffle_hog.cli.commands import scan

app = typer.Typer(
    name="aitruffle",
    help="AI Truffle Hog - AI API Key Secret Scanner",
    no_args_is_help=True,
)

app.add_typer(scan.app, name="scan")


@app.command()
def version():
    """Show version information."""
    from ai_truffle_hog import __version__
    typer.echo(f"AI Truffle Hog v{__version__}")


if __name__ == "__main__":
    app()
```

```python
# src/ai_truffle_hog/cli/commands/scan.py
"""Scan command."""

import asyncio
from pathlib import Path
from typing import Optional

import typer

from ai_truffle_hog.core.orchestrator import Orchestrator
from ai_truffle_hog.reporter.console import ConsoleReporter
from ai_truffle_hog.reporter.json_reporter import JSONReporter

app = typer.Typer()


@app.callback(invoke_without_command=True)
def scan(
    target: str = typer.Argument(
        ...,
        help="GitHub repository URL or file containing list of URLs",
    ),
    validate: bool = typer.Option(
        False,
        "--validate", "-v",
        help="Validate discovered keys against provider APIs",
    ),
    output: str = typer.Option(
        "table",
        "--output", "-o",
        help="Output format: table, json",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output-file", "-f",
        help="Write results to file",
    ),
    show_secrets: bool = typer.Option(
        False,
        "--show-secrets",
        help="Show full secret values (use with caution)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet", "-q",
        help="Minimal output",
    ),
):
    """Scan repositories for AI API keys."""
    console = ConsoleReporter(show_secrets=show_secrets, quiet=quiet)
    
    async def run():
        orchestrator = Orchestrator(
            validate=validate,
            callback=console.on_event if not quiet else None,
        )
        
        console.start()
        session = await orchestrator.run(target)
        console.finish(session)
        
        if output == "json" or output_file:
            json_reporter = JSONReporter(show_secrets=show_secrets)
            if output_file:
                json_reporter.write(session, output_file)
            elif output == "json":
                typer.echo(json_reporter.to_json(session))
        
        # Exit with code 1 if secrets found
        if session.total_secrets_found > 0:
            raise typer.Exit(code=1)
    
    asyncio.run(run())
```

**Acceptance Criteria:**
- `aitruffle --help` shows usage
- `aitruffle scan URL` scans a repository
- `aitruffle scan file.txt` scans multiple repos
- `--validate` flag enables validation
- `--output json` produces JSON output
- Exit code 1 when secrets found

**Dependencies:** Task 8.1, Tasks 7.1-7.3

---

## Phase 9: Testing and Documentation

### Task 9.1: Add Integration Tests

**Objective:** Create comprehensive integration tests.

**Input:** All components

**Actions:**
1. Test full scan workflow with real small repo
2. Test file list scanning
3. Test validation mocking
4. Test error handling

**Output Files:**
```
tests/integration/test_full_scan.py
tests/e2e/test_scan_command.py
```

**Acceptance Criteria:**
- Tests pass in CI
- Coverage > 80%

**Dependencies:** Task 8.2

---

### Task 9.2: Add E2E Tests

**Objective:** Test CLI end-to-end.

**Input:** CLI implementation

**Actions:**
1. Test CLI with subprocess
2. Verify exit codes
3. Verify output formats

**Output Files:**
```
tests/e2e/test_cli.py
```

**Acceptance Criteria:**
- CLI commands work as documented

**Dependencies:** Task 8.2

---

### Task 9.3: Complete Documentation

**Objective:** Update README and add usage documentation.

**Input:** All implementation

**Actions:**
1. Update README.md with complete usage
2. Add examples
3. Document configuration options
4. Add troubleshooting section

**Output Files:**
```
README.md (update)
docs/usage.md
docs/configuration.md
```

**Acceptance Criteria:**
- README has complete quick start
- All CLI options documented
- Configuration options documented

**Dependencies:** Task 8.2

---

## Execution Summary

### Phase 1 (Foundation): Tasks 1.1-1.4
- Creates project structure and configuration
- **Estimated effort:** 2-3 hours

### Phase 2 (Core Utilities): Tasks 2.1-2.4
- Implements data models and utilities
- **Estimated effort:** 2-3 hours

### Phase 3 (Providers): Tasks 3.1-3.6
- Implements all provider patterns and validation
- **Estimated effort:** 3-4 hours

### Phase 4 (Fetcher): Tasks 4.1-4.2
- Implements Git and file operations
- **Estimated effort:** 2 hours

### Phase 5 (Scanner): Task 5.1
- Implements pattern scanning engine
- **Estimated effort:** 2 hours

### Phase 6 (Validator): Tasks 6.1-6.2
- Implements async validation
- **Estimated effort:** 2-3 hours

### Phase 7 (Reporter): Tasks 7.1-7.3
- Implements output and logging
- **Estimated effort:** 2-3 hours

### Phase 8 (Integration): Tasks 8.1-8.2
- Implements orchestrator and CLI
- **Estimated effort:** 2-3 hours

### Phase 9 (Testing/Docs): Tasks 9.1-9.3
- Adds tests and documentation
- **Estimated effort:** 2-3 hours

**Total Estimated Effort:** 19-26 hours

---

## Task Dependencies Graph

```
Phase 1 ──┬── Task 1.1 ──► Task 1.2 ──► Task 1.3
          │                    │
          │                    └──► Task 1.4
          │
Phase 2 ──┼── Task 2.1 ◄── (depends on 1.1)
          │
          ├── Task 2.2 ◄── (depends on 1.1)
          │
          ├── Task 2.3 ◄── (depends on 1.1)
          │
          └── Task 2.4 ◄── (depends on 1.1)
                  │
Phase 3 ──┬── Task 3.1 ◄── (depends on 2.1)
          │       │
          ├── Task 3.2 ◄─┤
          ├── Task 3.3 ◄─┤
          ├── Task 3.4 ◄─┤
          ├── Task 3.5 ◄─┘
          │       │
          └── Task 3.6 ◄── (depends on 3.2-3.5)
                  │
Phase 4 ──┬── Task 4.1 ◄── (depends on 1.2)
          │
          └── Task 4.2 ◄── (depends on 2.4)
                  │
Phase 5 ──── Task 5.1 ◄── (depends on 3.6, 2.1, 2.2)
                  │
Phase 6 ──┬── Task 6.1 ◄── (depends on 3.6, 2.1)
          │
          └── Task 6.2 ◄── (depends on 1.1)
                  │
Phase 7 ──┬── Task 7.1 ◄── (depends on 2.3)
          │
          ├── Task 7.2 ◄── (depends on 2.1)
          │
          └── Task 7.3 ◄── (depends on 2.3, 2.4)
                  │
Phase 8 ──┬── Task 8.1 ◄── (depends on 4.1, 4.2, 5.1, 6.1)
          │       │
          └── Task 8.2 ◄── (depends on 8.1, 7.1-7.3)
                  │
Phase 9 ──┬── Task 9.1 ◄── (depends on 8.2)
          │
          ├── Task 9.2 ◄── (depends on 8.2)
          │
          └── Task 9.3 ◄── (depends on 8.2)
```
