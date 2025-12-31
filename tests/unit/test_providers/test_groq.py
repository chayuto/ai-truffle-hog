"""Unit tests for Groq provider implementation."""

import pytest

from ai_truffle_hog.providers.base import ValidationStatus
from ai_truffle_hog.providers.groq import GroqProvider


class TestGroqProviderProperties:
    """Tests for Groq provider properties."""

    def test_name(self) -> None:
        """Provider name is correct."""
        provider = GroqProvider()
        assert provider.name == "groq"

    def test_display_name(self) -> None:
        """Display name is correct."""
        provider = GroqProvider()
        assert provider.display_name == "Groq"

    def test_validation_endpoint(self) -> None:
        """Validation endpoint is correct."""
        provider = GroqProvider()
        assert provider.validation_endpoint == "https://api.groq.com/openai/v1/models"

    def test_auth_header_name(self) -> None:
        """Auth header name is correct."""
        provider = GroqProvider()
        assert provider.auth_header_name == "Authorization"

    def test_patterns_count(self) -> None:
        """Provider has expected number of patterns."""
        provider = GroqProvider()
        assert len(provider.patterns) == 1


class TestGroqProviderPatterns:
    """Tests for Groq key pattern matching."""

    @pytest.fixture
    def provider(self) -> GroqProvider:
        """Create provider instance."""
        return GroqProvider()

    def test_standard_key_pattern(self, provider: GroqProvider) -> None:
        """Standard gsk_ key is detected (50+ chars after prefix)."""
        # gsk_ + 50 alphanumeric = 54+ total
        key = "gsk_" + "a" * 50
        text = f"api_key = '{key}'"
        matches = provider.match(text)
        assert len(matches) == 1
        assert matches[0].group(1).startswith("gsk_")

    def test_longer_key(self, provider: GroqProvider) -> None:
        """Longer key is detected."""
        key = "gsk_" + "b" * 60
        text = f"GROQ_API_KEY={key}"
        matches = provider.match(text)
        assert len(matches) == 1

    def test_key_in_code(self, provider: GroqProvider) -> None:
        """Key in Python code is detected."""
        key = "gsk_" + "c" * 52
        text = f'token = "{key}"'
        matches = provider.match(text)
        assert len(matches) == 1

    def test_short_key_not_matched(self, provider: GroqProvider) -> None:
        """Key shorter than 50 chars after prefix is not matched."""
        key = "gsk_" + "d" * 40  # Only 40 chars after prefix
        text = f"api_key = '{key}'"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_wrong_prefix_not_matched(self, provider: GroqProvider) -> None:
        """Key without gsk_ prefix is not matched."""
        key = "gak_" + "e" * 50
        text = f"api_key = '{key}'"
        matches = provider.match(text)
        assert len(matches) == 0


class TestGroqProviderAuth:
    """Tests for Groq provider authentication."""

    def test_build_auth_header(self) -> None:
        """Auth header is formatted correctly."""
        provider = GroqProvider()
        key = "gsk_" + "f" * 50
        header = provider.build_auth_header(key)

        assert header == {"Authorization": f"Bearer {key}"}


class TestGroqProviderInterpretResponse:
    """Tests for Groq provider response interpretation."""

    @pytest.fixture
    def provider(self) -> GroqProvider:
        """Create provider instance."""
        return GroqProvider()

    def test_200_valid(self, provider: GroqProvider) -> None:
        """200 response indicates valid key."""
        result = provider.interpret_response(200, {"data": []})
        assert result.status == ValidationStatus.VALID

    def test_401_invalid(self, provider: GroqProvider) -> None:
        """401 response indicates invalid key."""
        result = provider.interpret_response(401, {"error": "Unauthorized"})
        assert result.status == ValidationStatus.INVALID

    def test_429_rate_limited(self, provider: GroqProvider) -> None:
        """429 response indicates rate limit."""
        result = provider.interpret_response(429, None)
        assert result.status == ValidationStatus.RATE_LIMITED

    def test_500_server_error(self, provider: GroqProvider) -> None:
        """500 response indicates server error."""
        result = provider.interpret_response(500, None)
        assert result.status == ValidationStatus.ERROR
