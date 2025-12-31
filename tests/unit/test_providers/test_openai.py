"""Unit tests for OpenAI provider implementation."""

import pytest

from ai_truffle_hog.providers.base import ValidationStatus
from ai_truffle_hog.providers.openai import OpenAIProvider


class TestOpenAIProviderProperties:
    """Tests for OpenAI provider properties."""

    def test_name(self) -> None:
        """Provider name is correct."""
        provider = OpenAIProvider()
        assert provider.name == "openai"

    def test_display_name(self) -> None:
        """Display name is correct."""
        provider = OpenAIProvider()
        assert provider.display_name == "OpenAI"

    def test_validation_endpoint(self) -> None:
        """Validation endpoint is correct."""
        provider = OpenAIProvider()
        assert provider.validation_endpoint == "https://api.openai.com/v1/models"

    def test_auth_header_name(self) -> None:
        """Auth header name is correct."""
        provider = OpenAIProvider()
        assert provider.auth_header_name == "Authorization"

    def test_patterns_count(self) -> None:
        """Provider has expected number of patterns."""
        provider = OpenAIProvider()
        assert len(provider.patterns) == 1


class TestOpenAIProviderPatterns:
    """Tests for OpenAI key pattern matching."""

    @pytest.fixture
    def provider(self) -> OpenAIProvider:
        """Create provider instance."""
        return OpenAIProvider()

    def test_standard_key_pattern(self, provider: OpenAIProvider) -> None:
        """Standard sk- key is detected."""
        text = "api_key = 'sk-abc123def456ghi789jkl012mno345pqr'"
        matches = provider.match(text)
        assert len(matches) == 1
        assert matches[0].group(1).startswith("sk-")

    def test_project_key_pattern(self, provider: OpenAIProvider) -> None:
        """Project key sk-proj- is detected."""
        text = "OPENAI_API_KEY=sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
        matches = provider.match(text)
        assert len(matches) == 1
        assert "sk-proj-" in matches[0].group(1)

    def test_org_key_pattern(self, provider: OpenAIProvider) -> None:
        """Organization key sk-org- is detected."""
        text = 'key = "sk-org-abcdefghijklmnop12345678901234567890"'
        matches = provider.match(text)
        assert len(matches) == 1

    def test_admin_key_pattern(self, provider: OpenAIProvider) -> None:
        """Admin key sk-admin- is detected."""
        text = "export KEY=sk-admin-xyz12345678901234567890abcdefghij"
        matches = provider.match(text)
        assert len(matches) == 1

    def test_svcacct_key_pattern(self, provider: OpenAIProvider) -> None:
        """Service account key sk-svcacct- is detected."""
        text = "secret: sk-svcacct-abc123456789012345678901234567890"
        matches = provider.match(text)
        assert len(matches) == 1

    def test_short_key_not_matched(self, provider: OpenAIProvider) -> None:
        """Key shorter than 20 chars is not matched."""
        text = "sk-tooshort123"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_multiple_keys_detected(self, provider: OpenAIProvider) -> None:
        """Multiple keys are detected in same text."""
        text = """
        key1 = "sk-abc123def456ghi789jkl012mno345pqr"
        key2 = "sk-proj-xyz987654321abcdefghijklmno"
        """
        matches = provider.match(text)
        assert len(matches) == 2

    def test_unrelated_text_not_matched(self, provider: OpenAIProvider) -> None:
        """Unrelated text is not matched."""
        text = "This is just some random text without any API keys."
        matches = provider.match(text)
        assert len(matches) == 0


class TestOpenAIProviderAuth:
    """Tests for OpenAI provider authentication."""

    def test_build_auth_header(self) -> None:
        """Auth header is formatted correctly."""
        provider = OpenAIProvider()
        key = "sk-test123456789012345678901234567890"
        header = provider.build_auth_header(key)

        assert header["Authorization"] == f"Bearer {key}"
        assert "Content-Type" in header


class TestOpenAIProviderInterpretResponse:
    """Tests for OpenAI provider response interpretation."""

    @pytest.fixture
    def provider(self) -> OpenAIProvider:
        """Create provider instance."""
        return OpenAIProvider()

    def test_200_valid(self, provider: OpenAIProvider) -> None:
        """200 response indicates valid key."""
        result = provider.interpret_response(200, {"data": []})
        assert result.status == ValidationStatus.VALID
        assert result.http_status_code == 200

    def test_401_invalid(self, provider: OpenAIProvider) -> None:
        """401 response indicates invalid key."""
        result = provider.interpret_response(401, {"error": "Unauthorized"})
        assert result.status == ValidationStatus.INVALID
        assert result.http_status_code == 401

    def test_429_quota_exceeded(self, provider: OpenAIProvider) -> None:
        """429 response indicates quota exceeded."""
        result = provider.interpret_response(429, None)
        assert result.status == ValidationStatus.QUOTA_EXCEEDED

    def test_500_server_error(self, provider: OpenAIProvider) -> None:
        """500 response indicates server error."""
        result = provider.interpret_response(500, None)
        assert result.status == ValidationStatus.ERROR

    def test_403_valid_scoped(self, provider: OpenAIProvider) -> None:
        """403 response indicates valid but scoped key."""
        result = provider.interpret_response(403, None)
        assert result.status == ValidationStatus.VALID
