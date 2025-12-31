"""Google Gemini API key provider implementation.

This module implements detection and validation for Google AI (Gemini) API keys.
Note: The AIza prefix is shared across many Google Cloud services.
"""

import re
from typing import ClassVar

from ai_truffle_hog.providers.base import (
    BaseProvider,
    ValidationResult,
    ValidationStatus,
)


class GoogleGeminiProvider(BaseProvider):
    """Google Gemini API key provider.

    Supports detection and validation of:
    - API keys: AIza prefix + 35 alphanumeric characters (39 total)

    Note: The AIza prefix is used by many Google services.
    Validation confirms if the key works with the Gemini API specifically.

    Unlike other providers, Google uses query parameter authentication
    instead of headers.
    """

    # Compiled patterns for key detection
    _patterns: ClassVar[list[re.Pattern[str]]] = [
        # API key: AIza prefix + 35 characters (alphanumeric, dash, underscore)
        re.compile(
            r"\b(AIza[0-9A-Za-z\-_]{35})\b",
            re.ASCII,
        ),
    ]

    @property
    def name(self) -> str:
        """Return provider identifier."""
        return "google_gemini"

    @property
    def display_name(self) -> str:
        """Return human-readable provider name."""
        return "Google Gemini"

    @property
    def patterns(self) -> list[re.Pattern[str]]:
        """Return compiled regex patterns for detection."""
        return self._patterns

    @property
    def validation_endpoint(self) -> str:
        """Return API endpoint for validation."""
        return "https://generativelanguage.googleapis.com/v1beta/models"

    @property
    def auth_header_name(self) -> str:
        """Return authentication header name.

        Google Gemini uses query parameter authentication, not headers.
        """
        return ""  # Empty - uses query parameter instead

    def build_auth_header(self, _key: str) -> dict[str, str]:
        """Build authentication headers for validation request.

        Google Gemini uses query parameter authentication, so this returns
        empty headers. Use build_validation_url() to get the full URL.

        Args:
            key: The Google API key (not used for headers).

        Returns:
            Empty dictionary.
        """
        return {}

    def build_validation_url(self, key: str) -> str:
        """Build validation URL with API key as query parameter.

        Args:
            key: The Google API key to validate.

        Returns:
            Full URL with key as query parameter.
        """
        return f"{self.validation_endpoint}?key={key}"

    def interpret_response(
        self,
        status_code: int,
        _response_body: dict[str, object] | None,
    ) -> ValidationResult:
        """Interpret HTTP response to determine key validity.

        Response code interpretation:
        - 200: Key is valid for Gemini API
        - 400: Key is invalid or wrong type
        - 403: Key is invalid or API not enabled

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
                message="Key is valid for Gemini API",
            )
        elif status_code in (400, 403):
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Key is invalid or not authorized for Gemini API",
            )
        elif status_code == 429:
            return ValidationResult(
                status=ValidationStatus.QUOTA_EXCEEDED,
                http_status_code=status_code,
                message="Key is valid but quota exceeded",
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
