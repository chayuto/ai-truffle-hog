"""Unit tests for Anthropic provider implementation."""

import pytest

from ai_truffle_hog.providers.anthropic import AnthropicProvider
from ai_truffle_hog.providers.base import ValidationStatus


class TestAnthropicProviderProperties:
    """Tests for Anthropic provider properties."""

    def test_name(self) -> None:
        """Provider name is correct."""
        provider = AnthropicProvider()
        assert provider.name == "anthropic"

    def test_display_name(self) -> None:
        """Display name is correct."""
        provider = AnthropicProvider()
        assert provider.display_name == "Anthropic"

    def test_validation_endpoint(self) -> None:
        """Validation endpoint is correct."""
        provider = AnthropicProvider()
        assert provider.validation_endpoint == "https://api.anthropic.com/v1/messages"

    def test_auth_header_name(self) -> None:
        """Auth header name is correct."""
        provider = AnthropicProvider()
        assert provider.auth_header_name == "x-api-key"

    def test_patterns_count(self) -> None:
        """Provider has expected number of patterns."""
        provider = AnthropicProvider()
        assert len(provider.patterns) == 2


class TestAnthropicProviderPatterns:
    """Tests for Anthropic key pattern matching."""

    @pytest.fixture
    def provider(self) -> AnthropicProvider:
        """Create provider instance."""
        return AnthropicProvider()

    def test_api_key_pattern(self, provider: AnthropicProvider) -> None:
        """Standard API key sk-ant-api- is detected."""
        # API keys have 80-120 chars after the prefix
        key_suffix = "a" * 85  # 85 chars after sk-ant-api03-
        text = f"api_key = 'sk-ant-api03-{key_suffix}'"
        matches = provider.match(text)
        assert len(matches) == 1
        assert matches[0].group(1).startswith("sk-ant-api")

    def test_admin_key_pattern(self, provider: AnthropicProvider) -> None:
        """Admin key sk-ant-admin- is detected."""
        # Admin keys have 20+ chars after the prefix
        key_suffix = "b" * 40
        text = f'ANTHROPIC_KEY="sk-ant-admin-{key_suffix}"'
        matches = provider.match(text)
        assert len(matches) == 1
        assert "sk-ant-admin" in matches[0].group(1)

    def test_different_api_versions(self, provider: AnthropicProvider) -> None:
        """Different API version numbers are detected."""
        key1_suffix = "c" * 85
        key2_suffix = "d" * 90
        text = f"""
        key1 = "sk-ant-api01-{key1_suffix}"
        key2 = "sk-ant-api02-{key2_suffix}"
        """
        matches = provider.match(text)
        assert len(matches) == 2

    def test_short_key_not_matched(self, provider: AnthropicProvider) -> None:
        """Key that's too short is not matched."""
        text = "sk-ant-api03-tooshort"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_wrong_prefix_not_matched(self, provider: AnthropicProvider) -> None:
        """Wrong prefix is not matched."""
        text = "sk-openai-abcdefghijklmnop12345678901234567890"
        matches = provider.match(text)
        assert len(matches) == 0


class TestAnthropicProviderAuth:
    """Tests for Anthropic provider authentication."""

    def test_build_auth_header(self) -> None:
        """Auth header includes x-api-key and anthropic-version."""
        provider = AnthropicProvider()
        key = "sk-ant-api03-test1234567890"
        header = provider.build_auth_header(key)

        assert header["x-api-key"] == key
        assert header["anthropic-version"] == "2023-06-01"
        assert header["Content-Type"] == "application/json"


class TestAnthropicProviderInterpretResponse:
    """Tests for Anthropic provider response interpretation."""

    @pytest.fixture
    def provider(self) -> AnthropicProvider:
        """Create provider instance."""
        return AnthropicProvider()

    def test_200_valid(self, provider: AnthropicProvider) -> None:
        """200 response indicates valid key."""
        result = provider.interpret_response(200, {"id": "msg_123"})
        assert result.status == ValidationStatus.VALID

    def test_400_with_credit_error(self, provider: AnthropicProvider) -> None:
        """400 with credit/balance error indicates quota exceeded."""
        body = {
            "error": {"message": "Your credit balance is too low to access the API."}
        }
        result = provider.interpret_response(400, body)
        assert result.status == ValidationStatus.QUOTA_EXCEEDED

    def test_400_regular_error(self, provider: AnthropicProvider) -> None:
        """400 without credit error indicates regular error."""
        body = {"error": {"message": "Invalid request parameters"}}
        result = provider.interpret_response(400, body)
        assert result.status == ValidationStatus.VALID  # Key is valid, just bad request

    def test_401_invalid(self, provider: AnthropicProvider) -> None:
        """401 response indicates invalid key."""
        result = provider.interpret_response(401, {"error": "Unauthorized"})
        assert result.status == ValidationStatus.INVALID

    def test_403_invalid(self, provider: AnthropicProvider) -> None:
        """403 response indicates invalid key."""
        result = provider.interpret_response(403, None)
        assert result.status == ValidationStatus.INVALID

    def test_429_rate_limited(self, provider: AnthropicProvider) -> None:
        """429 response indicates rate limit."""
        result = provider.interpret_response(429, None)
        assert result.status == ValidationStatus.RATE_LIMITED

    def test_500_server_error(self, provider: AnthropicProvider) -> None:
        """500 response indicates server error."""
        result = provider.interpret_response(500, None)
        assert result.status == ValidationStatus.ERROR
