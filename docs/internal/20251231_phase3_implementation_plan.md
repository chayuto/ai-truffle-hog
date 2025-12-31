# Phase 3: Provider Implementation Plan

**Date:** 2025-12-31  
**Phase:** 3 - Provider Implementation  
**Status:** In Progress

---

## Objective

Implement all AI provider classes that detect and validate API keys. Each provider implements the `BaseProvider` abstract class with:
- Regex patterns for key detection
- Validation endpoint configuration  
- Authentication header building
- Response interpretation logic

---

## Provider Summary

| Provider | Key Prefix | Pattern Complexity | Validation Method |
|----------|-----------|-------------------|-------------------|
| OpenAI | `sk-`, `sk-proj-`, `sk-org-` | Simple prefix | GET /v1/models |
| Anthropic | `sk-ant-api03-`, `sk-ant-admin-` | Prefix + version | POST /v1/messages |
| Hugging Face | `hf_` | Fixed length (37) | GET /api/whoami-v2 |
| Cohere | None (contextual) | Contextual (40 chars) | POST /v1/check-api-key |
| Replicate | `r8_` | Fixed length (40) | GET /v1/account |
| Google Gemini | `AIza` | Fixed length (39) | GET with query param |
| Groq | `gsk_` | Variable (50+) | GET /openai/v1/models |
| LangSmith | `lsv2_sk_`, `lsv2_pt_` | Prefix + type | GET /api/v1/sessions |

---

## Implementation Order

### Priority 1: High-usage providers (most likely to find in codebases)
1. **OpenAI** - Most common AI API key
2. **Anthropic** - Second most common
3. **Hugging Face** - Popular in ML community

### Priority 2: Growing providers  
4. **Groq** - Fast-growing OpenAI alternative
5. **Google Gemini** - Google's AI offering
6. **Replicate** - Model hosting platform

### Priority 3: Specialized providers
7. **Cohere** - Enterprise NLP
8. **LangSmith** - LangChain tooling

---

## File Structure

```
src/ai_truffle_hog/providers/
├── __init__.py          # Exports all providers
├── base.py              # BaseProvider ABC (already exists)
├── registry.py          # ProviderRegistry (already exists, needs update)
├── openai.py            # NEW
├── anthropic.py         # NEW
├── huggingface.py       # NEW
├── cohere.py            # NEW
├── replicate.py         # NEW
├── google.py            # NEW
├── groq.py              # NEW
└── langsmith.py         # NEW

tests/unit/test_providers/
├── __init__.py          # NEW
├── test_openai.py       # NEW
├── test_anthropic.py    # NEW
├── test_huggingface.py  # NEW
├── test_cohere.py       # NEW
├── test_replicate.py    # NEW
├── test_google.py       # NEW
├── test_groq.py         # NEW
└── test_langsmith.py    # NEW
```

---

## Pattern Specifications

### OpenAI Pattern
```python
r'\b(sk-(?:proj-|org-|admin-|svcacct-)?[a-zA-Z0-9]{20,150})\b'
```
- Matches: `sk-abc123...`, `sk-proj-xyz...`, `sk-org-...`
- Length: 20-150 chars after prefix

### Anthropic Patterns
```python
r'\b(sk-ant-api\d{2}-[a-zA-Z0-9\-_]{80,120})\b'  # API key
r'\b(sk-ant-admin-[a-zA-Z0-9\-_]{20,})\b'         # Admin key
```

### Hugging Face Pattern
```python
r'\b(hf_[a-zA-Z0-9]{34})\b'
```
- Fixed: 37 chars total (prefix + 34)

### Cohere Patterns (Contextual)
```python
r'(?i)(?:cohere)[^\n]{0,30}[\'\"]\s*([a-zA-Z0-9]{40})\s*[\'\"]'
r'(?i)COHERE_API_KEY\s*[=:]\s*[\'\"]*([a-zA-Z0-9]{40})[\'\"]*'
```
- Requires context (no unique prefix)

### Replicate Pattern
```python
r'\b(r8_[a-zA-Z0-9]{37})\b'
```
- Fixed: 40 chars total

### Google Gemini Pattern
```python
r'\b(AIza[0-9A-Za-z\-_]{35})\b'
```
- Fixed: 39 chars total
- Note: AIza prefix shared across Google services

### Groq Pattern
```python
r'\b(gsk_[a-zA-Z0-9]{50,})\b'
```
- Variable: 50+ chars after prefix

### LangSmith Pattern
```python
r'\b(lsv2_(?:sk|pt)_[a-zA-Z0-9]{32,})\b'
```
- sk = service key, pt = personal token

---

## Validation Endpoints

| Provider | Endpoint | Method | Auth Header |
|----------|----------|--------|-------------|
| OpenAI | `https://api.openai.com/v1/models` | GET | `Authorization: Bearer {key}` |
| Anthropic | `https://api.anthropic.com/v1/messages` | POST | `x-api-key: {key}` |
| Hugging Face | `https://huggingface.co/api/whoami-v2` | GET | `Authorization: Bearer {key}` |
| Cohere | `https://api.cohere.ai/v1/check-api-key` | POST | `Authorization: Bearer {key}` |
| Replicate | `https://api.replicate.com/v1/account` | GET | `Authorization: Bearer {key}` |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/models` | GET | `?key={key}` (query param) |
| Groq | `https://api.groq.com/openai/v1/models` | GET | `Authorization: Bearer {key}` |
| LangSmith | `https://api.smith.langchain.com/api/v1/sessions` | GET | `x-api-key: {key}` |

---

## Response Code Interpretation

### Standard Mappings
- `200` → VALID
- `401` → INVALID
- `403` → VALID (permission-scoped) or INVALID (depends on provider)
- `429` → RATE_LIMITED or QUOTA_EXCEEDED
- `5xx` → ERROR

### Provider-Specific Handling
- **Anthropic 400**: Check for "credit" in error → QUOTA_EXCEEDED
- **Cohere 200**: Check `valid` field in response body
- **Google 400/403**: Could be wrong key type, not just invalid

---

## Test Cases per Provider

Each provider test file should cover:

1. **Pattern Matching**
   - Valid keys match correctly
   - Invalid keys don't match
   - Edge cases (too short, too long, wrong chars)

2. **Response Interpretation**
   - 200 → VALID
   - 401 → INVALID
   - Provider-specific codes

3. **Header Building**
   - Correct header format
   - All required headers included

---

## Dependencies

- `BaseProvider` from `providers/base.py` (exists)
- `ValidationResult`, `ValidationStatus` from `providers/base.py` (exists)
- No external dependencies for implementation
- Tests use `pytest` only (mocking HTTP is done in integration tests)

---

## Execution Plan

1. Create all 8 provider implementation files
2. Create test directory structure
3. Create unit tests for each provider
4. Update registry to import and register all providers
5. Update providers/__init__.py with exports
6. Run lint and tests
7. Generate completion report
