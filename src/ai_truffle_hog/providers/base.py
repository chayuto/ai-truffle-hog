"""Base provider class and validation types.

This module defines the abstract base class that all provider implementations
must inherit from, along with validation result types.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ValidationStatus(str, Enum):
    """Result status of a key validation attempt."""

    VALID = "valid"
    INVALID = "invalid"
    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Result of a validation attempt against a provider API."""

    status: ValidationStatus
    http_status_code: Optional[int] = None
    message: Optional[str] = None
    metadata: dict[str, str] = field(default_factory=dict)


class BaseProvider(ABC):
    """Abstract base class for AI provider implementations.

    Each provider must implement methods for:
    - Pattern matching (regex patterns to detect keys)
    - Authentication header building
    - Response interpretation for validation
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'openai', 'anthropic').

        Returns:
            Lowercase string identifier for the provider.
        """
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider name (e.g., 'OpenAI', 'Anthropic').

        Returns:
            Display name for the provider.
        """
        ...

    @property
    @abstractmethod
    def patterns(self) -> list[re.Pattern[str]]:
        """Compiled regex patterns for detecting this provider's keys.

        Returns:
            List of compiled regex patterns.
        """
        ...

    @property
    @abstractmethod
    def validation_endpoint(self) -> str:
        """API endpoint URL for key validation.

        Returns:
            Full URL to the validation endpoint.
        """
        ...

    @property
    @abstractmethod
    def auth_header_name(self) -> str:
        """Name of the authentication header.

        Returns:
            Header name (e.g., 'Authorization', 'x-api-key').
        """
        ...

    @abstractmethod
    def build_auth_header(self, key: str) -> dict[str, str]:
        """Build authentication headers for validation request.

        Args:
            key: The API key to validate.

        Returns:
            Dictionary of headers to include in the request.
        """
        ...

    @abstractmethod
    def interpret_response(
        self,
        status_code: int,
        response_body: Optional[dict[str, object]],
    ) -> ValidationResult:
        """Interpret HTTP response to determine key validity.

        Args:
            status_code: HTTP status code from the response.
            response_body: Parsed JSON body if available.

        Returns:
            ValidationResult indicating the key's validity.
        """
        ...

    def match(self, text: str) -> list[re.Match[str]]:
        """Find all pattern matches in text.

        Args:
            text: Text to search for patterns.

        Returns:
            List of regex match objects.
        """
        matches: list[re.Match[str]] = []
        for pattern in self.patterns:
            matches.extend(pattern.finditer(text))
        return matches

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<{self.__class__.__name__}(name={self.name!r})>"
