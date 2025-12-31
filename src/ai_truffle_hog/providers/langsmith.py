"""LangSmith API key provider implementation.

This module implements detection and validation for LangSmith API keys,
which are used for LangChain observability and tracing.
"""

import re
from typing import ClassVar

from ai_truffle_hog.providers.base import (
    BaseProvider,
    ValidationResult,
    ValidationStatus,
)


class LangSmithProvider(BaseProvider):
    """LangSmith API key provider.

    Supports detection and validation of:
    - Service keys: lsv2_sk_ prefix + 32+ alphanumeric characters
    - Personal tokens: lsv2_pt_ prefix + 32+ alphanumeric characters

    Validation uses GET /api/v1/sessions endpoint with x-api-key header.
    """

    # Compiled patterns for key detection
    _patterns: ClassVar[list[re.Pattern[str]]] = [
        # Service key (sk) or personal token (pt)
        re.compile(
            r"\b(lsv2_(?:sk|pt)_[a-zA-Z0-9]{32,})\b",
            re.ASCII,
        ),
    ]

    @property
    def name(self) -> str:
        """Return provider identifier."""
        return "langsmith"

    @property
    def display_name(self) -> str:
        """Return human-readable provider name."""
        return "LangSmith"

    @property
    def patterns(self) -> list[re.Pattern[str]]:
        """Return compiled regex patterns for detection."""
        return self._patterns

    @property
    def validation_endpoint(self) -> str:
        """Return API endpoint for validation."""
        return "https://api.smith.langchain.com/api/v1/sessions"

    @property
    def auth_header_name(self) -> str:
        """Return authentication header name."""
        return "x-api-key"

    def build_auth_header(self, key: str) -> dict[str, str]:
        """Build authentication headers for validation request.

        LangSmith uses x-api-key header for authentication.

        Args:
            key: The LangSmith API key to validate.

        Returns:
            Headers dictionary with x-api-key.
        """
        return {"x-api-key": key}

    def interpret_response(
        self,
        status_code: int,
        _response_body: dict[str, object] | None,
    ) -> ValidationResult:
        """Interpret HTTP response to determine key validity.

        Response code interpretation:
        - 200: Key is valid and active
        - 401: Key is invalid or revoked
        - 403: Key is valid but lacks permissions

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
        elif status_code == 403:
            # 403 means valid key but lacks permissions
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid but lacks permissions",
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
