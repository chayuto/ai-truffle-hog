"""Cohere API key provider implementation.

This module implements detection and validation for Cohere API keys.
Cohere keys don't have a unique prefix, so detection relies on contextual patterns.
"""

import re
from typing import Any, ClassVar

from ai_truffle_hog.providers.base import (
    BaseProvider,
    ValidationResult,
    ValidationStatus,
)


class CohereProvider(BaseProvider):
    """Cohere API key provider.

    Cohere API keys are 40 alphanumeric characters without a unique prefix.
    Detection uses contextual patterns that look for:
    - Variable names containing 'cohere'
    - Environment variable COHERE_API_KEY

    Validation uses POST /v1/check-api-key endpoint.
    """

    # Compiled patterns for key detection (contextual)
    _patterns: ClassVar[list[re.Pattern[str]]] = [
        # Variable assignment with 'cohere' context
        re.compile(
            r"(?i)(?:cohere)[^\n]{0,30}['\"]([a-zA-Z0-9]{40})['\"]",
            re.ASCII,
        ),
        # Environment variable pattern
        re.compile(
            r"(?i)COHERE_API_KEY\s*[=:]\s*['\"]?([a-zA-Z0-9]{40})['\"]?",
            re.ASCII,
        ),
    ]

    @property
    def name(self) -> str:
        """Return provider identifier."""
        return "cohere"

    @property
    def display_name(self) -> str:
        """Return human-readable provider name."""
        return "Cohere"

    @property
    def patterns(self) -> list[re.Pattern[str]]:
        """Return compiled regex patterns for detection."""
        return self._patterns

    @property
    def validation_endpoint(self) -> str:
        """Return API endpoint for validation."""
        return "https://api.cohere.ai/v1/check-api-key"

    @property
    def auth_header_name(self) -> str:
        """Return authentication header name."""
        return "Authorization"

    def build_auth_header(self, key: str) -> dict[str, str]:
        """Build authentication headers for validation request.

        Args:
            key: The Cohere API key to validate.

        Returns:
            Headers dictionary with Bearer token authentication.
        """
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def get_validation_body(self) -> dict[str, Any]:
        """Return request body for validation.

        Cohere's check-api-key endpoint requires an empty body.

        Returns:
            Empty dictionary.
        """
        return {}

    def interpret_response(
        self,
        status_code: int,
        response_body: dict[str, object] | None,
    ) -> ValidationResult:
        """Interpret HTTP response to determine key validity.

        Response code interpretation:
        - 200: Check 'valid' field in response body
        - 401: Key is invalid

        Args:
            status_code: HTTP status code from the response.
            response_body: Parsed JSON body if available.

        Returns:
            ValidationResult with appropriate status.
        """
        if status_code == 200:
            is_valid = False
            if response_body:
                is_valid = bool(response_body.get("valid", False))

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
