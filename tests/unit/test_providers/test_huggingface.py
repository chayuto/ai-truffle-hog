"""Unit tests for Hugging Face provider implementation."""

import pytest

from ai_truffle_hog.providers.base import ValidationStatus
from ai_truffle_hog.providers.huggingface import HuggingFaceProvider


class TestHuggingFaceProviderProperties:
    """Tests for Hugging Face provider properties."""

    def test_name(self) -> None:
        """Provider name is correct."""
        provider = HuggingFaceProvider()
        assert provider.name == "huggingface"

    def test_display_name(self) -> None:
        """Display name is correct."""
        provider = HuggingFaceProvider()
        assert provider.display_name == "Hugging Face"

    def test_validation_endpoint(self) -> None:
        """Validation endpoint is correct."""
        provider = HuggingFaceProvider()
        assert provider.validation_endpoint == "https://huggingface.co/api/whoami-v2"

    def test_auth_header_name(self) -> None:
        """Auth header name is correct."""
        provider = HuggingFaceProvider()
        assert provider.auth_header_name == "Authorization"

    def test_patterns_count(self) -> None:
        """Provider has expected number of patterns."""
        provider = HuggingFaceProvider()
        assert len(provider.patterns) == 1


class TestHuggingFaceProviderPatterns:
    """Tests for Hugging Face token pattern matching."""

    @pytest.fixture
    def provider(self) -> HuggingFaceProvider:
        """Create provider instance."""
        return HuggingFaceProvider()

    def test_standard_token_pattern(self, provider: HuggingFaceProvider) -> None:
        """Standard hf_ token is detected (34 chars after prefix)."""
        # hf_ + 34 alphanumeric = 37 total
        text = "api_key = 'hf_1234567890abcdefghijklmnopqrstuv12'"
        matches = provider.match(text)
        assert len(matches) == 1
        assert matches[0].group(1).startswith("hf_")

    def test_token_in_env_var(self, provider: HuggingFaceProvider) -> None:
        """Token in environment variable is detected."""
        text = "HF_TOKEN=hf_abcdefghijklmnopqrstuvwxyz12345678"
        matches = provider.match(text)
        assert len(matches) == 1

    def test_token_in_code(self, provider: HuggingFaceProvider) -> None:
        """Token in Python code is detected."""
        text = 'token = "hf_XyZ123456789AbCdEfGhIjKlMnOpQrStUv"'
        matches = provider.match(text)
        assert len(matches) == 1

    def test_short_token_not_matched(self, provider: HuggingFaceProvider) -> None:
        """Token shorter than 37 chars is not matched."""
        text = "hf_tooshort123"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_wrong_prefix_not_matched(self, provider: HuggingFaceProvider) -> None:
        """Token without hf_ prefix is not matched."""
        text = "other_1234567890abcdefghijklmnopqrstuv"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_multiple_tokens_detected(self, provider: HuggingFaceProvider) -> None:
        """Multiple tokens are detected in same text."""
        text = """
        token1 = "hf_abcdefghijklmnopqrstuvwxyz12345678"
        token2 = "hf_ABCDEFGHIJKLMNOPQRSTUVWXYZ98765432"
        """
        matches = provider.match(text)
        assert len(matches) == 2


class TestHuggingFaceProviderAuth:
    """Tests for Hugging Face provider authentication."""

    def test_build_auth_header(self) -> None:
        """Auth header is formatted correctly."""
        provider = HuggingFaceProvider()
        key = "hf_abcdefghijklmnopqrstuvwxyz12345678"
        header = provider.build_auth_header(key)

        assert header == {"Authorization": f"Bearer {key}"}


class TestHuggingFaceProviderInterpretResponse:
    """Tests for Hugging Face provider response interpretation."""

    @pytest.fixture
    def provider(self) -> HuggingFaceProvider:
        """Create provider instance."""
        return HuggingFaceProvider()

    def test_200_valid_with_metadata(self, provider: HuggingFaceProvider) -> None:
        """200 response with user info returns metadata."""
        body = {
            "name": "testuser",
            "auth": {"accessToken": {"role": "read", "scopes": ["repo.write"]}},
        }
        result = provider.interpret_response(200, body)
        assert result.status == ValidationStatus.VALID
        assert result.metadata is not None
        assert result.metadata.get("username") == "testuser"

    def test_200_valid_without_metadata(self, provider: HuggingFaceProvider) -> None:
        """200 response without details still valid."""
        result = provider.interpret_response(200, {})
        assert result.status == ValidationStatus.VALID

    def test_401_invalid(self, provider: HuggingFaceProvider) -> None:
        """401 response indicates invalid token."""
        result = provider.interpret_response(401, {"error": "Unauthorized"})
        assert result.status == ValidationStatus.INVALID

    def test_429_error(self, provider: HuggingFaceProvider) -> None:
        """429 response indicates error (HF doesn't rate limit whoami)."""
        result = provider.interpret_response(429, None)
        assert result.status == ValidationStatus.ERROR

    def test_500_server_error(self, provider: HuggingFaceProvider) -> None:
        """500 response indicates server error."""
        result = provider.interpret_response(500, None)
        assert result.status == ValidationStatus.ERROR
