"""Hugging Face API key provider implementation.

This module implements detection and validation for Hugging Face API tokens,
which are commonly used for accessing models and the Inference API.
"""

import re
from typing import ClassVar

from ai_truffle_hog.providers.base import (
    BaseProvider,
    ValidationResult,
    ValidationStatus,
)


class HuggingFaceProvider(BaseProvider):
    """Hugging Face API key provider.

    Supports detection and validation of:
    - User access tokens: hf_xxxxx (37 characters total)

    Validation uses GET /api/whoami-v2 which returns user information
    and token scopes.
    """

    # Compiled patterns for key detection
    _patterns: ClassVar[list[re.Pattern[str]]] = [
        # User access token: hf_ prefix + 34 alphanumeric characters
        re.compile(
            r"\b(hf_[a-zA-Z0-9]{34})\b",
            re.ASCII,
        ),
    ]

    @property
    def name(self) -> str:
        """Return provider identifier."""
        return "huggingface"

    @property
    def display_name(self) -> str:
        """Return human-readable provider name."""
        return "Hugging Face"

    @property
    def patterns(self) -> list[re.Pattern[str]]:
        """Return compiled regex patterns for detection."""
        return self._patterns

    @property
    def validation_endpoint(self) -> str:
        """Return API endpoint for validation."""
        return "https://huggingface.co/api/whoami-v2"

    @property
    def auth_header_name(self) -> str:
        """Return authentication header name."""
        return "Authorization"

    def build_auth_header(self, key: str) -> dict[str, str]:
        """Build authentication headers for validation request.

        Args:
            key: The Hugging Face API token to validate.

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
        - 200: Token is valid, extracts user metadata
        - 401: Token is invalid or revoked
        - 403: Token is valid but lacks required scope

        Args:
            status_code: HTTP status code from the response.
            response_body: Parsed JSON body if available.

        Returns:
            ValidationResult with appropriate status and metadata.
        """
        if status_code == 200:
            metadata: dict[str, str] = {}
            if response_body:
                # Extract user information
                name = response_body.get("name")
                if name:
                    metadata["username"] = str(name)

                # Extract token scopes
                auth_info = response_body.get("auth", {})
                if isinstance(auth_info, dict):
                    token_info = auth_info.get("accessToken", {})
                    if isinstance(token_info, dict):
                        display_name = token_info.get("displayName")
                        if display_name:
                            metadata["token_name"] = str(display_name)
                        role = token_info.get("role")
                        if role:
                            metadata["role"] = str(role)

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
        elif status_code == 403:
            # 403 means valid token but lacks scope
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Token is valid but lacks required scope",
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
