"""Replicate API key provider implementation.

This module implements detection and validation for Replicate API tokens,
which are used for accessing the Replicate model hosting platform.
"""

import re
from typing import ClassVar

from ai_truffle_hog.providers.base import (
    BaseProvider,
    ValidationResult,
    ValidationStatus,
)


class ReplicateProvider(BaseProvider):
    """Replicate API key provider.

    Supports detection and validation of:
    - API tokens: r8_ prefix + 37 alphanumeric characters (40 total)

    Validation uses GET /v1/account endpoint.
    """

    # Compiled patterns for key detection
    _patterns: ClassVar[list[re.Pattern[str]]] = [
        # API token: r8_ prefix + 37 alphanumeric characters
        re.compile(
            r"\b(r8_[a-zA-Z0-9]{37})\b",
            re.ASCII,
        ),
    ]

    @property
    def name(self) -> str:
        """Return provider identifier."""
        return "replicate"

    @property
    def display_name(self) -> str:
        """Return human-readable provider name."""
        return "Replicate"

    @property
    def patterns(self) -> list[re.Pattern[str]]:
        """Return compiled regex patterns for detection."""
        return self._patterns

    @property
    def validation_endpoint(self) -> str:
        """Return API endpoint for validation."""
        return "https://api.replicate.com/v1/account"

    @property
    def auth_header_name(self) -> str:
        """Return authentication header name."""
        return "Authorization"

    def build_auth_header(self, key: str) -> dict[str, str]:
        """Build authentication headers for validation request.

        Args:
            key: The Replicate API token to validate.

        Returns:
            Headers dictionary with Bearer token authentication.
        """
        return {"Authorization": f"Bearer {key}"}

    def interpret_response(
        self,
        status_code: int,
        response_body: dict[str, object] | None,
    ) -> ValidationResult:
        """Interpret HTTP response to determine key validity.

        Response code interpretation:
        - 200: Token is valid and active
        - 401: Token is invalid or revoked

        Args:
            status_code: HTTP status code from the response.
            response_body: Parsed JSON body if available.

        Returns:
            ValidationResult with appropriate status.
        """
        if status_code == 200:
            metadata: dict[str, str] = {}
            if response_body:
                username = response_body.get("username")
                if username:
                    metadata["username"] = str(username)

            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Token is valid and active",
                metadata=metadata,
            )
        elif status_code == 401:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Token is invalid or revoked",
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
