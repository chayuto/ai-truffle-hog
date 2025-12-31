"""Anthropic API key provider implementation.

This module implements detection and validation for Anthropic API keys,
supporting both standard API keys and admin keys.
"""

import re
from typing import Any, ClassVar

from ai_truffle_hog.providers.base import (
    BaseProvider,
    ValidationResult,
    ValidationStatus,
)


class AnthropicProvider(BaseProvider):
    """Anthropic API key provider.

    Supports detection and validation of:
    - API keys: sk-ant-api03-xxx (version number may vary)
    - Admin keys: sk-ant-admin-xxx

    Validation uses POST /v1/messages with a minimal request body.
    Requires anthropic-version header.
    """

    # Anthropic API version for validation requests
    ANTHROPIC_VERSION = "2023-06-01"

    # Minimal model for validation (cheapest option)
    VALIDATION_MODEL = "claude-3-haiku-20240307"

    # Compiled patterns for key detection
    _patterns: ClassVar[list[re.Pattern[str]]] = [
        # API key pattern (version flexible: api01, api02, api03, etc.)
        re.compile(
            r"\b(sk-ant-api\d{2}-[a-zA-Z0-9\-_]{80,120})\b",
            re.ASCII,
        ),
        # Admin key pattern
        re.compile(
            r"\b(sk-ant-admin-[a-zA-Z0-9\-_]{20,})\b",
            re.ASCII,
        ),
    ]

    @property
    def name(self) -> str:
        """Return provider identifier."""
        return "anthropic"

    @property
    def display_name(self) -> str:
        """Return human-readable provider name."""
        return "Anthropic"

    @property
    def patterns(self) -> list[re.Pattern[str]]:
        """Return compiled regex patterns for detection."""
        return self._patterns

    @property
    def validation_endpoint(self) -> str:
        """Return API endpoint for validation."""
        return "https://api.anthropic.com/v1/messages"

    @property
    def auth_header_name(self) -> str:
        """Return authentication header name."""
        return "x-api-key"

    def build_auth_header(self, key: str) -> dict[str, str]:
        """Build authentication headers for validation request.

        Anthropic requires both x-api-key and anthropic-version headers.

        Args:
            key: The Anthropic API key to validate.

        Returns:
            Headers dictionary with API key and version.
        """
        return {
            "x-api-key": key,
            "anthropic-version": self.ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

    def get_validation_body(self) -> dict[str, Any]:
        """Return minimal request body for validation.

        Uses the cheapest model with minimal tokens to reduce cost.

        Returns:
            Request body dictionary.
        """
        return {
            "model": self.VALIDATION_MODEL,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "Hi"}],
        }

    def interpret_response(
        self,
        status_code: int,
        response_body: dict[str, object] | None,
    ) -> ValidationResult:
        """Interpret HTTP response to determine key validity.

        Response code interpretation:
        - 200: Key is valid and active
        - 401/403: Key is invalid or revoked
        - 400: Check for credit balance issue → QUOTA_EXCEEDED
        - 429: Rate limited

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

        if status_code in (401, 403):
            return ValidationResult(
                status=ValidationStatus.INVALID,
                http_status_code=status_code,
                message="Key is invalid or revoked",
            )

        if status_code == 400:
            # Check if it's a credit balance issue
            error_msg = ""
            if response_body:
                error_obj = response_body.get("error", {})
                if isinstance(error_obj, dict):
                    error_msg = str(error_obj.get("message", "")).lower()

            if "credit" in error_msg or "balance" in error_msg:
                return ValidationResult(
                    status=ValidationStatus.QUOTA_EXCEEDED,
                    http_status_code=status_code,
                    message="Key is valid but account has insufficient credits",
                )
            # 400 without credit issue means key is valid but bad request
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid (bad request parameters)",
            )

        if status_code == 429:
            return ValidationResult(
                status=ValidationStatus.RATE_LIMITED,
                http_status_code=status_code,
                message="Key is valid but rate limited",
            )

        # Server errors or unexpected responses
        return ValidationResult(
            status=ValidationStatus.ERROR,
            http_status_code=status_code,
            message=f"Server/unexpected error: {status_code}",
        )
