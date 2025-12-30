# AI-Truffle-Hog: Architectural Analysis & Design Decisions

**Document Version:** 1.0  
**Date:** 2025-12-31  
**Author:** Architecture Analysis  
**Status:** Reference Document

---

## 1. Executive Summary

This document synthesizes findings from all research documents to establish architectural decisions for the AI-Truffle-Hog POC and CLI tool. The project aims to build a Python-based secret scanner specifically targeting AI provider API keys (OpenAI, Anthropic, Hugging Face, etc.) with validation capabilities.

---

## 2. Scope Definition for POC

### 2.1 In-Scope (POC Phase)

| Feature | Description | Priority |
|---------|-------------|----------|
| **GitHub Repository Scanning** | Single URL or list of URLs as input | P0 |
| **AI Provider Pattern Detection** | OpenAI, Anthropic, Hugging Face, Cohere, Replicate, Google Gemini | P0 |
| **Key Validation** | Live API calls to verify key validity | P0 |
| **CLI Interface** | Typer-based CLI with rich output | P0 |
| **Structured Logging** | JSON-formatted logs with configurable levels | P0 |
| **Local Development** | venv-based development environment | P0 |

### 2.2 Out-of-Scope (POC Phase)

- AI/ML-based false positive reduction (Phase 2)
- Pre-commit hooks
- CI/CD integration
- SARIF output
- Git history traversal (beyond HEAD)
- Real-time GitHub event streaming

---

## 3. Technology Stack Decisions

### 3.1 Language: Python

**Rationale from Research:**
- Research explicitly states: *"Python base for POC, CLI base"*
- Python offers unrivaled ecosystem for rapid prototyping
- Research document recommends Python for POC despite Go's performance advantages
- Machine Learning integration path (future: SetFit, ONNX) aligns with Python

**Constraints Addressed:**
- GIL limitation mitigated via `asyncio` for I/O-bound validation
- Memory management via streaming patterns where applicable

### 3.2 CLI Framework: Typer

**Rationale from Research (AI-Truffle-Hog Project Research Plan.md):**
> "Typer is built on top of Click, Typer utilizes standard Python type hints to enforce CLI behavior. Type Safety: If the CLI expects a list of URLs, defining the argument as `targets: List[str]` allows Typer to handle parsing and validation automatically."

**Key Benefits:**
- Type safety via Python type hints
- Auto-generated help documentation
- Pydantic integration for validation
- Reduces boilerplate vs argparse/click

### 3.3 HTTP Client: httpx (async)

**Rationale from Research:**
> "Validation involves network I/O... The architecture must utilize asyncio and an asynchronous HTTP client like httpx or aiohttp to validate found secrets in parallel."

**Selection: `httpx` over `aiohttp`:**
- Modern API design
- Both sync and async support in same library
- Better integration with Pydantic
- Simpler timeout/retry handling

### 3.4 Git Operations: PyDriller + GitPython

**Rationale from Research:**
> "PyDriller is a framework explicitly designed for Mining Software Repositories (MSR). PyDriller traverses commits using Python generators, meaning it only loads the metadata and diff of the current commit being analyzed into memory."

**For POC (HEAD-only scanning):**
- GitPython for simple cloning operations
- PyDriller reserved for future history traversal

### 3.5 Logging: structlog + JSON

**Rationale from Research:**
> "Logs must be machine-parsable. The tool should utilize the structlog library or Python's standard logging with a JSON formatter."

**Requirements:**
- ISO 8601 timestamps
- Structured fields: level, component, repo_url, commit_hash, event
- Secret redaction before writing

---

## 4. Provider Pattern Analysis

### 4.1 Pattern Registry (from AI Provider API Key Scanning Research.md)

| Provider | Prefix | Regex Pattern | Validation Endpoint | Auth Header |
|----------|--------|---------------|---------------------|-------------|
| **OpenAI** | `sk-`, `sk-proj-`, `sk-org-` | `\b(sk-(?:proj-\|org-\|admin-)?[a-zA-Z0-9]{20,150})\b` | `GET /v1/models` | `Authorization: Bearer` |
| **Anthropic** | `sk-ant-api03-` | `\b(sk-ant-api\d{2}-[a-zA-Z0-9\-_]{80,120})\b` | `POST /v1/messages` | `x-api-key` |
| **Hugging Face** | `hf_` | `\b(hf_[a-zA-Z0-9]{34})\b` | `GET /api/whoami-v2` | `Authorization: Bearer` |
| **Cohere** | None (contextual) | `[a-zA-Z0-9]{40}` | `POST /v1/check-api-key` | `Authorization: Bearer` |
| **Replicate** | `r8_` | `\b(r8_[a-zA-Z0-9]{37})\b` | `GET /v1/predictions` | `Authorization: Bearer` |
| **Google Gemini** | `AIza` | `\b(AIza[0-9A-Za-z\-_]{35})\b` | `GET /v1beta/models?key=` | Query param |
| **Groq** | `gsk_` | `\b(gsk_[a-zA-Z0-9]{50,})\b` | `GET /openai/v1/models` | `Authorization: Bearer` |
| **LangSmith** | `lsv2_sk_`, `lsv2_pt_` | `\b(lsv2_(?:sk\|pt)_[a-zA-Z0-9]{32,})\b` | `GET /api/v1/sessions` | `x-api-key` |
| **Perplexity** | `pplx-` | `\b(pplx-[a-zA-Z0-9]{40,})\b` | `GET /chat/completions` | `Authorization: Bearer` |
| **Deepgram** | None | `[a-zA-Z0-9]{40}` | `GET /v1/auth/token` | `Authorization: Token` |

### 4.2 Validation Response Interpretation

**Critical Insight from Research:**
> "HTTP 429 Too Many Requests: The key is valid but the account has exceeded rate limits... From a security perspective, this must be treated as a Valid result."

**Status Code Mapping:**
```
200 OK           → VALID (active)
401 Unauthorized → INVALID (dead/revoked)
403 Forbidden    → VALID (valid but permission-scoped)
429 Rate Limited → VALID (valid but quota exceeded)
400 Bad Request  → CONTEXT-DEPENDENT (check error body)
```

---

## 5. Component Architecture

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer (Typer)                       │
│  • Input parsing (URL/file)                                     │
│  • Output formatting (JSON/table)                               │
│  • Progress indicators                                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator (Core)                        │
│  • Input handler (URL vs file detection)                        │
│  • Scan session management                                      │
│  • Result aggregation                                           │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────────┐    ┌───────────────┐
│   Fetcher     │     │    Scanner        │    │   Validator   │
│ (GitPython)   │     │ (Regex Engine)    │    │ (httpx async) │
│               │     │                   │    │               │
│ • Clone repo  │     │ • Pattern match   │    │ • Verify key  │
│ • File enum   │     │ • Extract context │    │ • Rate limit  │
│ • Cleanup     │     │ • Generate cands  │    │ • Retry logic │
└───────────────┘     └───────────────────┘    └───────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Reporter (Output)                          │
│  • Console (rich/table)                                         │
│  • JSON file                                                    │
│  • Logging (structlog)                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Module Breakdown

```
ai_truffle_hog/
├── __init__.py
├── __main__.py              # Entry point
├── cli/
│   ├── __init__.py
│   ├── app.py               # Typer app definition
│   └── commands/
│       ├── __init__.py
│       └── scan.py          # Main scan command
├── core/
│   ├── __init__.py
│   ├── orchestrator.py      # Scan orchestration
│   ├── scanner.py           # Pattern matching engine
│   └── models.py            # Pydantic models
├── providers/
│   ├── __init__.py
│   ├── base.py              # Abstract provider class
│   ├── openai.py
│   ├── anthropic.py
│   ├── huggingface.py
│   ├── cohere.py
│   ├── replicate.py
│   ├── google.py
│   ├── groq.py
│   ├── langsmith.py
│   └── registry.py          # Provider registration
├── fetcher/
│   ├── __init__.py
│   ├── git.py               # Git clone/fetch operations
│   └── file_walker.py       # File enumeration
├── validator/
│   ├── __init__.py
│   ├── client.py            # Async HTTP client
│   └── rate_limiter.py      # Rate limiting logic
├── reporter/
│   ├── __init__.py
│   ├── console.py           # Rich console output
│   ├── json_reporter.py     # JSON file output
│   └── log_handler.py       # Logging setup
├── utils/
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   ├── redaction.py         # Secret redaction
│   └── entropy.py           # Shannon entropy calculation
└── config/
    ├── default.toml         # Default configuration
    └── patterns.toml        # Provider patterns (extensible)
```

---

## 6. Data Flow

### 6.1 Single Repository Scan Flow

```
1. INPUT: User provides repo URL
   └── CLI parses: `aitruffle scan https://github.com/user/repo`

2. FETCH: Clone repository to temp directory
   └── GitPython shallow clone (--depth 1)
   └── Enumerate text files (extension filter)

3. SCAN: Pattern matching across files
   └── Load provider patterns from registry
   └── Apply regex patterns to file contents
   └── Extract match context (±5 lines)
   └── Generate Candidate objects

4. VALIDATE (optional): Verify key liveness
   └── For each candidate, call provider validation endpoint
   └── Interpret HTTP response
   └── Update candidate status (VALID/INVALID/UNKNOWN)

5. REPORT: Output results
   └── Console table with findings
   └── JSON file with full details
   └── Structured logs

6. CLEANUP: Remove temp directory
```

### 6.2 Candidate Model

```python
class SecretCandidate(BaseModel):
    """Represents a potential secret found during scanning."""
    
    # Identification
    id: UUID
    provider: str              # e.g., "openai", "anthropic"
    
    # Location
    file_path: str
    line_number: int
    column_start: int
    column_end: int
    
    # Content
    secret_value: str          # The actual key (redacted in logs)
    context_before: str        # 5 lines before
    context_after: str         # 5 lines after
    variable_name: Optional[str]  # Extracted var name if available
    
    # Metadata
    pattern_matched: str       # Which regex pattern
    entropy_score: float       # Shannon entropy
    
    # Validation
    validation_status: Literal["pending", "valid", "invalid", "error", "skipped"]
    validation_timestamp: Optional[datetime]
    validation_details: Optional[str]  # Error message or additional info
```

---

## 7. Configuration System

### 7.1 Configuration Hierarchy

```
1. Built-in defaults (config/default.toml)
2. User config file (~/.config/ai-truffle-hog/config.toml)
3. Project config file (.ai-truffle-hog.toml in repo root)
4. Environment variables (ATH_*)
5. CLI flags (highest priority)
```

### 7.2 Default Configuration

```toml
[scanner]
file_extensions = [".py", ".js", ".ts", ".env", ".json", ".yaml", ".yml", ".toml", ".xml", ".properties", ".conf", ".go", ".rb", ".php", ".java", ".kt", ".swift"]
max_file_size_kb = 1024
skip_paths = ["node_modules", ".git", "__pycache__", "venv", ".venv", "dist", "build"]
entropy_threshold = 4.5

[validator]
enabled = true
timeout_seconds = 10
max_concurrent = 5
retry_count = 3
retry_delay_seconds = 1

[logging]
level = "INFO"
format = "json"
file = "ai-truffle-hog.log"
redact_secrets = true

[output]
format = "table"  # or "json"
show_context = true
context_lines = 3
```

---

## 8. Logging Strategy

### 8.1 Log Levels and Events

| Level | Event | Description |
|-------|-------|-------------|
| DEBUG | `scan_file_start` | Beginning to scan a file |
| DEBUG | `pattern_match` | Raw regex match found |
| INFO | `scan_start` | Scan session initiated |
| INFO | `repo_clone` | Repository cloned successfully |
| INFO | `secret_found` | Candidate secret identified |
| INFO | `validation_result` | Key validation completed |
| INFO | `scan_complete` | Scan session finished |
| WARNING | `validation_timeout` | Validation request timed out |
| WARNING | `rate_limit_hit` | API rate limit encountered |
| ERROR | `clone_failed` | Repository clone failed |
| ERROR | `validation_error` | Validation request failed |

### 8.2 Log Entry Structure

```json
{
  "timestamp": "2025-12-31T10:30:00.000Z",
  "level": "INFO",
  "component": "scanner",
  "event": "secret_found",
  "repo_url": "https://github.com/user/repo",
  "commit_hash": "abc123",
  "file_path": "src/config.py",
  "line_number": 42,
  "provider": "openai",
  "secret_preview": "sk-proj-****...",
  "entropy": 5.2
}
```

### 8.3 Redaction Rules

**From Research:**
> "A common vulnerability in secret scanners is that they log the secrets they find to disk in plain text, creating a new leak."

**Redaction Strategy:**
- Default: Show first 8 chars + `****` + last 4 chars
- `--show-secrets` flag: Full secret (with warning)
- Never log full secrets at INFO level or above

---

## 9. Error Handling Strategy

### 9.1 Error Categories

| Category | Examples | Handling |
|----------|----------|----------|
| **Input Errors** | Invalid URL, file not found | Immediate exit with helpful message |
| **Network Errors** | Clone failed, validation timeout | Retry with backoff, then skip |
| **Parse Errors** | Binary file, encoding issues | Log warning, skip file |
| **Validation Errors** | API errors, rate limits | Retry, then mark as "error" |
| **System Errors** | Disk full, permission denied | Exit with error code |

### 9.2 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success, no secrets found |
| 1 | Success, secrets found |
| 2 | Input/configuration error |
| 3 | Network/clone error |
| 4 | System error |

---

## 10. Testing Strategy

### 10.1 Test Categories

| Type | Coverage | Tools |
|------|----------|-------|
| **Unit Tests** | Pattern matching, entropy calc, redaction | pytest |
| **Integration Tests** | Git operations, file walking | pytest + fixtures |
| **Validation Tests** | API mocking | pytest + respx |
| **E2E Tests** | Full scan flows | pytest + temp repos |

### 10.2 Test Data

- Synthetic secrets (generated, not real)
- Known false positives (UUIDs, hashes)
- Edge cases (binary files, large files)

---

## 11. Dependencies Summary

### 11.1 Core Dependencies

```
typer[all]>=0.9.0          # CLI framework
httpx>=0.27.0              # Async HTTP client
pydantic>=2.0.0            # Data validation
structlog>=24.0.0          # Structured logging
gitpython>=3.1.0           # Git operations
rich>=13.0.0               # Rich console output
tomli>=2.0.0               # TOML parsing (Python < 3.11)
```

### 11.2 Development Dependencies

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
respx>=0.21.0              # HTTP mocking
ruff>=0.5.0                # Linting + formatting
mypy>=1.10.0               # Type checking
pre-commit>=3.7.0
```

---

## 12. Security Considerations

### 12.1 Operational Security

**From Research (GitHub Repo Scanner Plan.md):**
> "Active verification exposes the scanner's infrastructure to the API providers... The verification worker must route requests through a rotating residential or datacenter proxy network."

**For POC:**
- Default: Direct validation (acceptable for personal use)
- Warning when validating many keys
- Rate limiting to avoid IP bans

### 12.2 Legal Considerations

**From Research:**
> "Using a key to validate it might inadvertently modify state if the wrong endpoint is used. This highlights the critical importance of using 'safe' endpoints like GET /models or GET /user rather than POST /completions or POST /train."

**POC Safeguards:**
- Only use read-only validation endpoints
- Clear documentation of validation behavior
- `--no-validate` flag for passive scanning

---

## 13. Future Considerations (Post-POC)

### Phase 2: ML-Based False Positive Reduction
- SetFit model for context classification
- ONNX export for portable deployment

### Phase 3: History Traversal
- PyDriller integration for full history scan
- Commit-based deduplication

### Phase 4: CI/CD Integration
- GitHub Actions workflow
- Pre-commit hooks
- SARIF output

### Phase 5: Scale
- Concurrent repository scanning
- Redis-based deduplication
- Event stream ingestion

---

## 14. References

1. AI Provider API Key Scanning Research.md - Pattern specifications
2. AI-Truffle-Hog Project Research Plan.md - Architecture blueprint
3. GitHub Repo Scanner Plan.md - Scale considerations
4. Global-Scale GitHub Secret Scanning_ Serverless Ar....md - Go-based design
5. Stack Configuration Comparison for Workflows.md - Language tradeoffs
