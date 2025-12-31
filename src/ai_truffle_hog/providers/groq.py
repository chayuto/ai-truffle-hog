"""Groq API key provider implementation.

This module implements detection and validation for Groq API keys.
Groq provides fast inference with an OpenAI-compatible API.
"""

import re
from typing import ClassVar

from ai_truffle_hog.providers.base import (
    BaseProvider,
    ValidationResult,
    ValidationStatus,
)


class GroqProvider(BaseProvider):
    """Groq API key provider.

    Supports detection and validation of:
    - API keys: gsk_ prefix + 50+ alphanumeric characters

    Groq uses an OpenAI-compatible API, so validation uses /openai/v1/models.
    """

    # Compiled patterns for key detection
    _patterns: ClassVar[list[re.Pattern[str]]] = [
        # API key: gsk_ prefix + 50+ alphanumeric characters
        re.compile(
            r"\b(gsk_[a-zA-Z0-9]{50,})\b",
            re.ASCII,
        ),
    ]

    @property
    def name(self) -> str:
        """Return provider identifier."""
        return "groq"

    @property
    def display_name(self) -> str:
        """Return human-readable provider name."""
        return "Groq"

    @property
    def patterns(self) -> list[re.Pattern[str]]:
        """Return compiled regex patterns for detection."""
        return self._patterns

    @property
    def validation_endpoint(self) -> str:
        """Return API endpoint for validation."""
        return "https://api.groq.com/openai/v1/models"

    @property
    def auth_header_name(self) -> str:
        """Return authentication header name."""
        return "Authorization"

    def build_auth_header(self, key: str) -> dict[str, str]:
        """Build authentication headers for validation request.

        Args:
            key: The Groq API key to validate.

        Returns:
            Headers dictionary with Bearer token authentication.
        """
        return {"Authorization": f"Bearer {key}"}

    def interpret_response(
        self,
        status_code: int,
        _response_body: dict[str, object] | None,
    ) -> ValidationResult:
        """Interpret HTTP response to determine key validity.

        Response code interpretation:
        - 200: Key is valid and active
        - 401: Key is invalid or revoked

        Args:
            status_code: HTTP status code from the response.
            response_body: Parsed JSON body if available.

        Returns:
            ValidationResult with appropriate status.
        """
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
        elif status_code == 429:
            return ValidationResult(
                status=ValidationStatus.RATE_LIMITED,
                http_status_code=status_code,
                message="Rate limited",
            )
        elif 500 <= status_code < 600:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Server error: {status_code}",
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                http_status_code=status_code,
                message=f"Unexpected response: {status_code}",
            )
