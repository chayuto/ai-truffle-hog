# AI-Truffle-Hog: Provider Implementation Specification

**Document Version:** 1.0  
**Date:** 2025-12-31  
**Author:** Architecture Analysis  
**Status:** Implementation Specification

---

## 1. Overview

This document provides detailed specifications for implementing each AI provider's secret detection pattern and validation logic. Each provider section includes regex patterns, validation endpoints, authentication methods, and response interpretation.

---

## 2. Provider Base Class Specification

### 2.1 Abstract Base Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import re


class ValidationStatus(Enum):
    """Result of key validation attempt."""
    VALID = "valid"              # Key is active and working
    INVALID = "invalid"          # Key is revoked, expired, or malformed
    QUOTA_EXCEEDED = "quota"     # Key is valid but account has no credits
    RATE_LIMITED = "rate_limit"  # Key is valid but rate limited
    ERROR = "error"              # Validation failed (network, timeout)
    SKIPPED = "skipped"          # Validation not attempted


@dataclass
class ValidationResult:
    """Result of a validation attempt."""
    status: ValidationStatus
    http_status_code: Optional[int] = None
    message: Optional[str] = None
    metadata: Optional[dict] = None  # Provider-specific info


class BaseProvider(ABC):
    """Abstract base class for AI provider implementations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'openai')."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'OpenAI')."""
        pass
    
    @property
    @abstractmethod
    def patterns(self) -> list[re.Pattern]:
        """Compiled regex patterns for detection."""
        pass
    
    @property
    @abstractmethod
    def validation_endpoint(self) -> str:
        """API endpoint for validation."""
        pass
    
    @property
    @abstractmethod
    def auth_header_name(self) -> str:
        """Header name for authentication."""
        pass
    
    @abstractmethod
    def build_auth_header(self, key: str) -> dict[str, str]:
        """Build authentication headers for validation request."""
        pass
    
    @abstractmethod
    def interpret_response(
        self, 
        status_code: int, 
        response_body: dict | None
    ) -> ValidationResult:
        """Interpret HTTP response to determine key validity."""
        pass
    
    def match(self, text: str) -> list[re.Match]:
        """Find all matches in text."""
        matches = []
        for pattern in self.patterns:
            matches.extend(pattern.finditer(text))
        return matches
```

---

## 3. OpenAI Provider

### 3.1 Pattern Specification

| Format | Prefix | Example | Length |
|--------|--------|---------|--------|
| Legacy User Key | `sk-` | `sk-abc123...xyz789` | ~51 chars |
| Project Key | `sk-proj-` | `sk-proj-abc123...xyz789` | 100+ chars |
| Organization Key | `sk-org-` | `sk-org-abc123...xyz789` | Variable |
| Admin Key | `sk-admin-` | `sk-admin-abc123...xyz789` | Variable |
| Service Account | `sk-svcacct-` | `sk-svcacct-abc123...xyz789` | Variable |

### 3.2 Regex Patterns

```python
OPENAI_PATTERNS = [
    # Standard pattern covering all sk- variants
    re.compile(
        r'\b(sk-(?:proj-|org-|admin-|svcacct-)?[a-zA-Z0-9]{20,150})\b',
        re.ASCII
    ),
]
```

### 3.3 Validation Specification

```yaml
endpoint: https://api.openai.com/v1/models
method: GET
headers:
  Authorization: "Bearer {key}"
  Content-Type: "application/json"

response_interpretation:
  200: VALID
  401: INVALID
  403: VALID  # Valid but permission-scoped
  429: QUOTA_EXCEEDED  # Valid but rate limited
  500-599: ERROR
```

### 3.4 Implementation

```python
class OpenAIProvider(BaseProvider):
    """OpenAI API key provider."""
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def display_name(self) -> str:
        return "OpenAI"
    
    @property
    def patterns(self) -> list[re.Pattern]:
        return [
            re.compile(
                r'\b(sk-(?:proj-|org-|admin-|svcacct-)?[a-zA-Z0-9]{20,150})\b',
                re.ASCII
            ),
        ]
    
    @property
    def validation_endpoint(self) -> str:
        return "https://api.openai.com/v1/models"
    
    @property
    def auth_header_name(self) -> str:
        return "Authorization"
    
    def build_auth_header(self, key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
    
    def interpret_response(
        self, 
        status_code: int, 
        response_body: dict | None
    ) -> ValidationResult:
        if status_code == 200:
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid and active",
            )
        elif status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Key is invalid or revoked",
            )
        elif status_code == 403:
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid but lacks permissions for this endpoint",
            )
        elif status_code == 429:
            return ValidationResult(
                status=ValidationStatus.QUOTA_EXCEEDED,
                http_status_code=status_code,
                message="Key is valid but quota exceeded or rate limited",
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Unexpected response: {status_code}",
            )
```

---

## 4. Anthropic Provider

### 4.1 Pattern Specification

| Format | Prefix | Example | Length |
|--------|--------|---------|--------|
| API Key v3 | `sk-ant-api03-` | `sk-ant-api03-abc123...` | 95-120 chars |
| Admin Key | `sk-ant-admin-` | `sk-ant-admin-abc123...` | Variable |

### 4.2 Regex Patterns

```python
ANTHROPIC_PATTERNS = [
    # Standard API key pattern (version flexible)
    re.compile(
        r'\b(sk-ant-api\d{2}-[a-zA-Z0-9\-_]{80,120})\b',
        re.ASCII
    ),
    # Admin key pattern
    re.compile(
        r'\b(sk-ant-admin-[a-zA-Z0-9\-_]{20,})\b',
        re.ASCII
    ),
]
```

### 4.3 Validation Specification

```yaml
endpoint: https://api.anthropic.com/v1/messages
method: POST
headers:
  x-api-key: "{key}"
  anthropic-version: "2023-06-01"
  Content-Type: "application/json"
body:
  model: "claude-3-haiku-20240307"
  max_tokens: 1
  messages:
    - role: "user"
      content: "Hi"

response_interpretation:
  200: VALID
  401: INVALID
  400:
    - "credit balance": QUOTA_EXCEEDED
    - other: ERROR
  429: RATE_LIMITED
```

### 4.4 Implementation

```python
class AnthropicProvider(BaseProvider):
    """Anthropic API key provider."""
    
    ANTHROPIC_VERSION = "2023-06-01"
    VALIDATION_MODEL = "claude-3-haiku-20240307"
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def display_name(self) -> str:
        return "Anthropic"
    
    @property
    def patterns(self) -> list[re.Pattern]:
        return [
            re.compile(
                r'\b(sk-ant-api\d{2}-[a-zA-Z0-9\-_]{80,120})\b',
                re.ASCII
            ),
            re.compile(
                r'\b(sk-ant-admin-[a-zA-Z0-9\-_]{20,})\b',
                re.ASCII
            ),
        ]
    
    @property
    def validation_endpoint(self) -> str:
        return "https://api.anthropic.com/v1/messages"
    
    @property
    def auth_header_name(self) -> str:
        return "x-api-key"
    
    def build_auth_header(self, key: str) -> dict[str, str]:
        return {
            "x-api-key": key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
    
    def get_validation_body(self) -> dict:
        """Returns the minimal request body for validation."""
        return {
            "model": self.VALIDATION_MODEL,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "Hi"}],
        }
    
    def interpret_response(
        self, 
        status_code: int, 
        response_body: dict | None
    ) -> ValidationResult:
        if status_code == 200:
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid and active",
            )
        elif status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Key is invalid or revoked",
            )
        elif status_code == 400:
            # Check if it's a credit balance issue
            error_msg = ""
            if response_body:
                error_msg = str(response_body.get("error", {}).get("message", "")).lower()
            
            if "credit" in error_msg or "balance" in error_msg:
                return ValidationResult(
                    status=ValidationStatus.QUOTA_EXCEEDED,
                    http_status_code=status_code,
                    message="Key is valid but account has insufficient credits",
                )
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Bad request: {error_msg}",
            )
        elif status_code == 429:
            return ValidationResult(
                status=ValidationStatus.RATE_LIMITED,
                http_status_code=status_code,
                message="Key is valid but rate limited",
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Unexpected response: {status_code}",
            )
```

---

## 5. Hugging Face Provider

### 5.1 Pattern Specification

| Format | Prefix | Example | Length |
|--------|--------|---------|--------|
| User Access Token | `hf_` | `hf_abcdefghijklmnopqrstuvwxyz123456` | 37 chars (prefix + 34) |

### 5.2 Regex Patterns

```python
HUGGINGFACE_PATTERNS = [
    re.compile(
        r'\b(hf_[a-zA-Z0-9]{34})\b',
        re.ASCII
    ),
]
```

### 5.3 Validation Specification

```yaml
endpoint: https://huggingface.co/api/whoami-v2
method: GET
headers:
  Authorization: "Bearer {key}"

response_interpretation:
  200: VALID
  401: INVALID
  403: VALID  # Token valid but lacks scope

metadata_extraction:
  - name: username
  - scopes: read, write, etc.
```

### 5.4 Implementation

```python
class HuggingFaceProvider(BaseProvider):
    """Hugging Face API key provider."""
    
    @property
    def name(self) -> str:
        return "huggingface"
    
    @property
    def display_name(self) -> str:
        return "Hugging Face"
    
    @property
    def patterns(self) -> list[re.Pattern]:
        return [
            re.compile(r'\b(hf_[a-zA-Z0-9]{34})\b', re.ASCII),
        ]
    
    @property
    def validation_endpoint(self) -> str:
        return "https://huggingface.co/api/whoami-v2"
    
    @property
    def auth_header_name(self) -> str:
        return "Authorization"
    
    def build_auth_header(self, key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {key}"}
    
    def interpret_response(
        self, 
        status_code: int, 
        response_body: dict | None
    ) -> ValidationResult:
        if status_code == 200:
            metadata = {}
            if response_body:
                metadata = {
                    "username": response_body.get("name"),
                    "scopes": response_body.get("auth", {}).get("accessToken", {}).get("displayName"),
                }
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid and active",
                metadata=metadata,
            )
        elif status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Key is invalid or revoked",
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Unexpected response: {status_code}",
            )
```

---

## 6. Cohere Provider

### 6.1 Pattern Specification

| Format | Prefix | Example | Length |
|--------|--------|---------|--------|
| API Key | None | `abcdefghijklmnopqrstuvwxyz1234567890ABCD` | 40 chars |

**Note:** Cohere keys lack a prefix. Detection requires contextual analysis.

### 6.2 Regex Patterns

```python
# Contextual pattern - looks for "cohere" near a 40-char string
COHERE_PATTERNS = [
    # Variable assignment pattern
    re.compile(
        r'(?i)(?:cohere)[^\n]{0,30}[\'\"]\s*([a-zA-Z0-9]{40})\s*[\'\"]',
        re.ASCII
    ),
    # Environment variable pattern
    re.compile(
        r'(?i)COHERE_API_KEY\s*[=:]\s*[\'\"]*([a-zA-Z0-9]{40})[\'\"]*',
        re.ASCII
    ),
]
```

### 6.3 Validation Specification

```yaml
endpoint: https://api.cohere.ai/v1/check-api-key
method: POST
headers:
  Authorization: "Bearer {key}"
  Content-Type: "application/json"
body: {}

response_interpretation:
  200:
    valid: true -> VALID
    valid: false -> INVALID
  401: INVALID
```

### 6.4 Implementation

```python
class CohereProvider(BaseProvider):
    """Cohere API key provider."""
    
    @property
    def name(self) -> str:
        return "cohere"
    
    @property
    def display_name(self) -> str:
        return "Cohere"
    
    @property
    def patterns(self) -> list[re.Pattern]:
        return [
            re.compile(
                r'(?i)(?:cohere)[^\n]{0,30}[\'\"]\s*([a-zA-Z0-9]{40})\s*[\'\"]',
                re.ASCII
            ),
            re.compile(
                r'(?i)COHERE_API_KEY\s*[=:]\s*[\'\"]*([a-zA-Z0-9]{40})[\'\"]*',
                re.ASCII
            ),
        ]
    
    @property
    def validation_endpoint(self) -> str:
        return "https://api.cohere.ai/v1/check-api-key"
    
    @property
    def auth_header_name(self) -> str:
        return "Authorization"
    
    def build_auth_header(self, key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
    
    def get_validation_body(self) -> dict:
        return {}
    
    def interpret_response(
        self, 
        status_code: int, 
        response_body: dict | None
    ) -> ValidationResult:
        if status_code == 200:
            is_valid = response_body.get("valid", False) if response_body else False
            if is_valid:
                return ValidationResult(
                    status=ValidationStatus.VALID,
                    http_status_code=status_code,
                    message="Key is valid and active",
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    http_status_code=status_code,
                    message="Key validation returned invalid",
                )
        elif status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Key is invalid",
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Unexpected response: {status_code}",
            )
```

---

## 7. Replicate Provider

### 7.1 Pattern Specification

| Format | Prefix | Example | Length |
|--------|--------|---------|--------|
| API Token | `r8_` | `r8_abcdefghijklmnopqrstuvwxyz1234567` | 40 chars |

### 7.2 Regex Patterns

```python
REPLICATE_PATTERNS = [
    re.compile(r'\b(r8_[a-zA-Z0-9]{37})\b', re.ASCII),
]
```

### 7.3 Validation Specification

```yaml
endpoint: https://api.replicate.com/v1/account
method: GET
headers:
  Authorization: "Bearer {key}"

response_interpretation:
  200: VALID
  401: INVALID
```

### 7.4 Implementation

```python
class ReplicateProvider(BaseProvider):
    """Replicate API key provider."""
    
    @property
    def name(self) -> str:
        return "replicate"
    
    @property
    def display_name(self) -> str:
        return "Replicate"
    
    @property
    def patterns(self) -> list[re.Pattern]:
        return [
            re.compile(r'\b(r8_[a-zA-Z0-9]{37})\b', re.ASCII),
        ]
    
    @property
    def validation_endpoint(self) -> str:
        return "https://api.replicate.com/v1/account"
    
    @property
    def auth_header_name(self) -> str:
        return "Authorization"
    
    def build_auth_header(self, key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {key}"}
    
    def interpret_response(
        self, 
        status_code: int, 
        response_body: dict | None
    ) -> ValidationResult:
        if status_code == 200:
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid and active",
            )
        elif status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Key is invalid or revoked",
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Unexpected response: {status_code}",
            )
```

---

## 8. Google Gemini Provider

### 8.1 Pattern Specification

| Format | Prefix | Example | Length |
|--------|--------|---------|--------|
| API Key | `AIza` | `AIzaSyAbcdefghijklmnopqrstuvwxyz12345` | 39 chars |

**Note:** The `AIza` prefix is shared across Google Cloud services. Validation determines if it's a Gemini key.

### 8.2 Regex Patterns

```python
GOOGLE_PATTERNS = [
    re.compile(r'\b(AIza[0-9A-Za-z\-_]{35})\b', re.ASCII),
]
```

### 8.3 Validation Specification

```yaml
endpoint: https://generativelanguage.googleapis.com/v1beta/models
method: GET
auth_method: query_parameter
query_params:
  key: "{key}"

response_interpretation:
  200: VALID (Gemini key)
  400: INVALID or wrong key type
  403: INVALID or API not enabled
```

### 8.4 Implementation

```python
class GoogleGeminiProvider(BaseProvider):
    """Google Gemini API key provider."""
    
    @property
    def name(self) -> str:
        return "google_gemini"
    
    @property
    def display_name(self) -> str:
        return "Google Gemini"
    
    @property
    def patterns(self) -> list[re.Pattern]:
        return [
            re.compile(r'\b(AIza[0-9A-Za-z\-_]{35})\b', re.ASCII),
        ]
    
    @property
    def validation_endpoint(self) -> str:
        return "https://generativelanguage.googleapis.com/v1beta/models"
    
    @property
    def auth_header_name(self) -> str:
        return ""  # Uses query parameter instead
    
    def build_auth_header(self, key: str) -> dict[str, str]:
        # Google uses query parameter, not header
        return {}
    
    def build_validation_url(self, key: str) -> str:
        """Build URL with API key as query parameter."""
        return f"{self.validation_endpoint}?key={key}"
    
    def interpret_response(
        self, 
        status_code: int, 
        response_body: dict | None
    ) -> ValidationResult:
        if status_code == 200:
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid for Gemini API",
            )
        elif status_code in (400, 403):
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Key is invalid or not authorized for Gemini API",
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Unexpected response: {status_code}",
            )
```

---

## 9. Groq Provider

### 9.1 Pattern Specification

| Format | Prefix | Example | Length |
|--------|--------|---------|--------|
| API Key | `gsk_` | `gsk_abcdefghijklmnopqrstuvwxyz...` | 50+ chars |

### 9.2 Regex Patterns

```python
GROQ_PATTERNS = [
    re.compile(r'\b(gsk_[a-zA-Z0-9]{50,})\b', re.ASCII),
]
```

### 9.3 Validation Specification

```yaml
endpoint: https://api.groq.com/openai/v1/models
method: GET
headers:
  Authorization: "Bearer {key}"

response_interpretation:
  200: VALID
  401: INVALID
```

### 9.4 Implementation

```python
class GroqProvider(BaseProvider):
    """Groq API key provider (OpenAI-compatible)."""
    
    @property
    def name(self) -> str:
        return "groq"
    
    @property
    def display_name(self) -> str:
        return "Groq"
    
    @property
    def patterns(self) -> list[re.Pattern]:
        return [
            re.compile(r'\b(gsk_[a-zA-Z0-9]{50,})\b', re.ASCII),
        ]
    
    @property
    def validation_endpoint(self) -> str:
        return "https://api.groq.com/openai/v1/models"
    
    @property
    def auth_header_name(self) -> str:
        return "Authorization"
    
    def build_auth_header(self, key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {key}"}
    
    def interpret_response(
        self, 
        status_code: int, 
        response_body: dict | None
    ) -> ValidationResult:
        if status_code == 200:
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid and active",
            )
        elif status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Key is invalid or revoked",
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Unexpected response: {status_code}",
            )
```

---

## 10. LangSmith Provider

### 10.1 Pattern Specification

| Format | Prefix | Example | Length |
|--------|--------|---------|--------|
| Service Key | `lsv2_sk_` | `lsv2_sk_abcdef123456...` | 40+ chars |
| Personal Token | `lsv2_pt_` | `lsv2_pt_abcdef123456...` | 40+ chars |

### 10.2 Regex Patterns

```python
LANGSMITH_PATTERNS = [
    re.compile(r'\b(lsv2_(?:sk|pt)_[a-zA-Z0-9]{32,})\b', re.ASCII),
]
```

### 10.3 Validation Specification

```yaml
endpoint: https://api.smith.langchain.com/api/v1/sessions
method: GET
headers:
  x-api-key: "{key}"

response_interpretation:
  200: VALID
  401: INVALID
  403: VALID (valid but permission-scoped)
```

### 10.4 Implementation

```python
class LangSmithProvider(BaseProvider):
    """LangSmith API key provider."""
    
    @property
    def name(self) -> str:
        return "langsmith"
    
    @property
    def display_name(self) -> str:
        return "LangSmith"
    
    @property
    def patterns(self) -> list[re.Pattern]:
        return [
            re.compile(r'\b(lsv2_(?:sk|pt)_[a-zA-Z0-9]{32,})\b', re.ASCII),
        ]
    
    @property
    def validation_endpoint(self) -> str:
        return "https://api.smith.langchain.com/api/v1/sessions"
    
    @property
    def auth_header_name(self) -> str:
        return "x-api-key"
    
    def build_auth_header(self, key: str) -> dict[str, str]:
        return {"x-api-key": key}
    
    def interpret_response(
        self, 
        status_code: int, 
        response_body: dict | None
    ) -> ValidationResult:
        if status_code == 200:
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid and active",
            )
        elif status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Key is invalid or revoked",
            )
        elif status_code == 403:
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid but lacks permissions",
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Unexpected response: {status_code}",
            )
```

---

## 11. Provider Registry

### 11.1 Registry Implementation

```python
from typing import Dict, Type


class ProviderRegistry:
    """Registry for all supported AI providers."""
    
    _providers: Dict[str, BaseProvider] = {}
    
    @classmethod
    def register(cls, provider: BaseProvider) -> None:
        """Register a provider instance."""
        cls._providers[provider.name] = provider
    
    @classmethod
    def get(cls, name: str) -> BaseProvider | None:
        """Get a provider by name."""
        return cls._providers.get(name)
    
    @classmethod
    def all(cls) -> list[BaseProvider]:
        """Get all registered providers."""
        return list(cls._providers.values())
    
    @classmethod
    def names(cls) -> list[str]:
        """Get all provider names."""
        return list(cls._providers.keys())


def initialize_providers() -> None:
    """Initialize and register all providers."""
    providers = [
        OpenAIProvider(),
        AnthropicProvider(),
        HuggingFaceProvider(),
        CohereProvider(),
        ReplicateProvider(),
        GoogleGeminiProvider(),
        GroqProvider(),
        LangSmithProvider(),
    ]
    for provider in providers:
        ProviderRegistry.register(provider)
```

---

## 12. Pattern Priority and Collision Handling

### 12.1 Prefix Collision Matrix

| Pattern | Providers | Resolution Strategy |
|---------|-----------|---------------------|
| `sk-` | OpenAI, Stability AI | Check length; validate against both |
| `AIza` | Google Maps, Firebase, Gemini | Validate against Gemini endpoint |

### 12.2 Resolution Order

1. **Longest prefix match first** - `sk-proj-` before `sk-`
2. **Most specific pattern first**
3. **Validation determines actual provider**

---

## 13. Testing Considerations

### 13.1 Test Keys

For testing, use obviously fake keys that match patterns:

```python
TEST_KEYS = {
    "openai": "sk-test123456789012345678901234567890123456789012345678",
    "anthropic": "sk-ant-api03-" + "a" * 95,
    "huggingface": "hf_" + "a" * 34,
    "replicate": "r8_" + "a" * 37,
    "groq": "gsk_" + "a" * 50,
    "langsmith": "lsv2_sk_" + "a" * 32,
}
```

### 13.2 Mocking Validation

Use `respx` to mock HTTP responses during testing:

```python
import respx
from httpx import Response

@respx.mock
async def test_openai_validation():
    respx.get("https://api.openai.com/v1/models").mock(
        return_value=Response(200, json={"data": []})
    )
    # ... test code
```
