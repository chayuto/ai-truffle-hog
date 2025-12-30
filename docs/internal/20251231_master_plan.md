# AI-Truffle-Hog: Implementation Master Plan

**Document Version:** 1.0  
**Date:** 2025-12-31  
**Author:** Architecture Analysis  
**Status:** Master Reference Document

---

## 1. Executive Summary

This document provides a comprehensive overview of the AI-Truffle-Hog POC implementation plan. It consolidates findings from all research documents and provides a complete blueprint for building a Python-based CLI tool that scans GitHub repositories for AI provider API keys.

### 1.1 Project Goals

| Goal | Description | Priority |
|------|-------------|----------|
| **Secret Detection** | Detect AI API keys in GitHub repositories | P0 |
| **Key Validation** | Verify if detected keys are active | P0 |
| **CLI Interface** | User-friendly command-line interface | P0 |
| **Structured Logging** | Machine-parsable JSON logs | P0 |
| **Developer Experience** | Easy local development setup | P0 |

### 1.2 Scope

**In Scope (POC):**
- Single repo URL or file with list of URLs as input
- Pattern detection for 8+ AI providers
- Optional live key validation
- Console and JSON output
- Structured logging
- venv-based local development

**Out of Scope (Future):**
- ML-based false positive reduction
- Git history traversal beyond HEAD
- Pre-commit hooks / CI integration
- SARIF output
- Real-time GitHub event streaming

---

## 2. Documentation Index

The implementation is documented across four detailed specification documents:

### 2.1 [20251231_architecture_analysis.md](20251231_architecture_analysis.md)

**Purpose:** Architectural decisions and component design

**Contents:**
- Scope definition for POC
- Technology stack decisions (Python, Typer, httpx, structlog)
- Provider pattern analysis (8 providers)
- Component architecture diagram
- Module breakdown
- Data flow diagrams
- Configuration system design
- Logging strategy
- Error handling approach
- Testing strategy
- Security considerations

### 2.2 [20251231_project_setup_spec.md](20251231_project_setup_spec.md)

**Purpose:** Project configuration and development environment

**Contents:**
- Complete directory tree specification
- Python version requirements (3.11+)
- Virtual environment setup instructions
- Complete pyproject.toml specification
- .gitignore configuration
- Pre-commit hook configuration
- VS Code settings
- Development setup script
- GitHub Actions CI workflow
- README.md template
- Dependency lock strategy

### 2.3 [20251231_provider_specification.md](20251231_provider_specification.md)

**Purpose:** Detailed provider implementation specifications

**Contents:**
- Base provider abstract class
- OpenAI provider (sk-, sk-proj-, sk-org-)
- Anthropic provider (sk-ant-api03-)
- Hugging Face provider (hf_)
- Cohere provider (contextual)
- Replicate provider (r8_)
- Google Gemini provider (AIza)
- Groq provider (gsk_)
- LangSmith provider (lsv2_)
- Provider registry implementation
- Collision handling
- Test key specifications

### 2.4 [20251231_coding_tasks.md](20251231_coding_tasks.md)

**Purpose:** Executable task breakdown for coding agents

**Contents:**
- 25 discrete implementation tasks
- 9 implementation phases
- Task dependencies and ordering
- Code specifications for each task
- Acceptance criteria
- Effort estimates (19-26 hours total)

---

## 3. Technology Stack Summary

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Language** | Python 3.11+ | ML ecosystem, rapid prototyping |
| **CLI Framework** | Typer | Type hints, auto-documentation |
| **HTTP Client** | httpx | Async support, modern API |
| **Data Validation** | Pydantic v2 | Type safety, settings management |
| **Git Operations** | GitPython | Repository cloning |
| **Console Output** | Rich | Tables, progress, colors |
| **Logging** | structlog | Structured JSON logs |
| **Linting** | Ruff | Fast, comprehensive |
| **Type Checking** | mypy | Static analysis |
| **Testing** | pytest | Standard, async support |

---

## 4. Supported Providers

| Provider | Prefix | Validation Endpoint | Auth Method |
|----------|--------|---------------------|-------------|
| OpenAI | `sk-`, `sk-proj-` | GET /v1/models | Bearer |
| Anthropic | `sk-ant-api03-` | POST /v1/messages | x-api-key |
| Hugging Face | `hf_` | GET /api/whoami-v2 | Bearer |
| Cohere | (contextual) | POST /v1/check-api-key | Bearer |
| Replicate | `r8_` | GET /v1/account | Bearer |
| Google Gemini | `AIza` | GET /v1beta/models | Query param |
| Groq | `gsk_` | GET /openai/v1/models | Bearer |
| LangSmith | `lsv2_sk_`, `lsv2_pt_` | GET /api/v1/sessions | x-api-key |

---

## 5. Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (Typer)                             │
│   aitruffle scan <url|file> [--validate] [--output json]        │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator                                │
│   Coordinates: Fetch → Scan → Validate → Report                 │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────────┐    ┌───────────────┐
│   GitFetcher  │     │     Scanner       │    │   Validator   │
│               │     │                   │    │               │
│ Clone repos   │     │ Pattern matching  │    │ Verify keys   │
│ Enumerate     │     │ Context extract   │    │ Rate limiting │
└───────────────┘     └───────────────────┘    └───────────────┘
                                │
                                ▼
                      ┌───────────────────┐
                      │  ProviderRegistry │
                      │                   │
                      │ OpenAI, Anthropic │
                      │ HuggingFace, etc. │
                      └───────────────────┘
                                │
                                ▼
                      ┌───────────────────┐
                      │     Reporter      │
                      │                   │
                      │ Console + JSON    │
                      │ Structured logs   │
                      └───────────────────┘
```

---

## 6. Implementation Phases

### Phase 1: Project Foundation (Tasks 1.1-1.4)
- Project structure
- Configuration files
- Development scripts
- CI/CD setup

### Phase 2: Core Utilities (Tasks 2.1-2.4)
- Data models (Pydantic)
- Entropy calculation
- Secret redaction
- Configuration system

### Phase 3: Provider Implementation (Tasks 3.1-3.6)
- Base provider class
- Individual provider implementations
- Provider registry

### Phase 4: Fetcher Implementation (Tasks 4.1-4.2)
- Git repository cloning
- File enumeration and filtering

### Phase 5: Scanner Implementation (Task 5.1)
- Pattern matching engine
- Context extraction
- Candidate generation

### Phase 6: Validator Implementation (Tasks 6.1-6.2)
- Async HTTP validation
- Rate limiting

### Phase 7: Reporter Implementation (Tasks 7.1-7.3)
- Console output (Rich)
- JSON output
- Logging setup (structlog)

### Phase 8: Integration (Tasks 8.1-8.2)
- Orchestrator implementation
- CLI application

### Phase 9: Testing & Documentation (Tasks 9.1-9.3)
- Integration tests
- E2E tests
- Documentation

---

## 7. CLI Usage Preview

```bash
# Scan a single repository
aitruffle scan https://github.com/user/repo

# Scan with validation
aitruffle scan https://github.com/user/repo --validate

# Scan multiple repos from file
aitruffle scan repos.txt --validate

# Output as JSON
aitruffle scan https://github.com/user/repo --output json

# Write results to file
aitruffle scan https://github.com/user/repo --output-file results.json

# Show full secrets (use with caution)
aitruffle scan https://github.com/user/repo --show-secrets

# Quiet mode
aitruffle scan https://github.com/user/repo -q
```

---

## 8. Expected Output Format

### 8.1 Console Output (Default)

```
AI Truffle Hog v0.1.0
Scanning: https://github.com/user/repo

⠋ Cloning repository...
✓ Cloned (commit: abc1234)
⠋ Scanning files... (42 files)
✓ Scan complete

┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Provider ┃ Secret                 ┃ File   ┃ Status           ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ openai   │ sk-proj-****...****xyz │ .env   │ ✓ Valid          │
│ anthropic│ sk-ant-****...****abc  │ config │ ✗ Invalid        │
└──────────┴────────────────────────┴────────┴──────────────────┘

Summary: 2 secrets found, 1 valid, 1 invalid
```

### 8.2 JSON Output

```json
{
  "session_id": "...",
  "started_at": "2025-12-31T10:00:00Z",
  "completed_at": "2025-12-31T10:00:30Z",
  "results": [
    {
      "repo_url": "https://github.com/user/repo",
      "commit_hash": "abc1234",
      "files_scanned": 42,
      "secrets_found": [
        {
          "provider": "openai",
          "secret_value": "sk-proj-****...****xyz",
          "file_path": ".env",
          "line_number": 3,
          "validation_status": "valid"
        }
      ]
    }
  ]
}
```

---

## 9. Effort Estimation

| Phase | Tasks | Hours |
|-------|-------|-------|
| Foundation | 1.1-1.4 | 2-3 |
| Core Utilities | 2.1-2.4 | 2-3 |
| Providers | 3.1-3.6 | 3-4 |
| Fetcher | 4.1-4.2 | 2 |
| Scanner | 5.1 | 2 |
| Validator | 6.1-6.2 | 2-3 |
| Reporter | 7.1-7.3 | 2-3 |
| Integration | 8.1-8.2 | 2-3 |
| Testing/Docs | 9.1-9.3 | 2-3 |
| **Total** | **25 tasks** | **19-26 hours** |

---

## 10. Success Criteria

### 10.1 Functional Requirements

- [ ] Scan single GitHub repository URL
- [ ] Scan list of URLs from file
- [ ] Detect secrets from all 8 providers
- [ ] Validate keys against provider APIs
- [ ] Output results to console (table format)
- [ ] Output results to JSON file
- [ ] Structured JSON logging
- [ ] Secret redaction in output/logs

### 10.2 Non-Functional Requirements

- [ ] Python 3.11+ compatibility
- [ ] Async validation for performance
- [ ] Clean temp directory after scan
- [ ] Graceful error handling
- [ ] Exit code 1 when secrets found
- [ ] < 2 second startup time

### 10.3 Developer Experience

- [ ] One-command setup (`./scripts/dev_setup.sh`)
- [ ] Pre-commit hooks working
- [ ] All tests passing
- [ ] Type checking passing
- [ ] Linting passing
- [ ] 80%+ test coverage

---

## 11. Next Steps

1. **For Coding Agent:**
   - Start with Phase 1 tasks (project structure)
   - Follow task order in `20251231_coding_tasks.md`
   - Reference specifications in other documents
   - Run tests after each task

2. **For Human Review:**
   - Verify task completion
   - Test CLI functionality
   - Review code quality
   - Update documentation as needed

---

## 12. References

### Research Documents
1. `AI Provider API Key Scanning Research.md` - Pattern specifications
2. `AI-Truffle-Hog Project Research Plan.md` - Architecture blueprint
3. `GitHub Repo Scanner Plan.md` - Scale considerations
4. `Global-Scale GitHub Secret Scanning_ Serverless Ar....md` - Go design
5. `Stack Configuration Comparison for Workflows.md` - Language tradeoffs

### Internal Documents
1. `20251231_architecture_analysis.md` - Architecture decisions
2. `20251231_project_setup_spec.md` - Project configuration
3. `20251231_provider_specification.md` - Provider implementations
4. `20251231_coding_tasks.md` - Task breakdown

---

*Document generated: 2025-12-31*
