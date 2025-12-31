"""Unit tests for LangSmith provider implementation."""

import pytest

from ai_truffle_hog.providers.base import ValidationStatus
from ai_truffle_hog.providers.langsmith import LangSmithProvider


class TestLangSmithProviderProperties:
    """Tests for LangSmith provider properties."""

    def test_name(self) -> None:
        """Provider name is correct."""
        provider = LangSmithProvider()
        assert provider.name == "langsmith"

    def test_display_name(self) -> None:
        """Display name is correct."""
        provider = LangSmithProvider()
        assert provider.display_name == "LangSmith"

    def test_validation_endpoint(self) -> None:
        """Validation endpoint is correct."""
        provider = LangSmithProvider()
        assert "smith.langchain.com" in provider.validation_endpoint

    def test_auth_header_name(self) -> None:
        """Auth header name is correct."""
        provider = LangSmithProvider()
        assert provider.auth_header_name == "x-api-key"

    def test_patterns_count(self) -> None:
        """Provider has expected number of patterns."""
        provider = LangSmithProvider()
        assert len(provider.patterns) == 1


class TestLangSmithProviderPatterns:
    """Tests for LangSmith key pattern matching."""

    @pytest.fixture
    def provider(self) -> LangSmithProvider:
        """Create provider instance."""
        return LangSmithProvider()

    def test_service_key_pattern(self, provider: LangSmithProvider) -> None:
        """Service key lsv2_sk_ is detected."""
        key = "lsv2_sk_" + "a" * 32
        text = f"api_key = '{key}'"
        matches = provider.match(text)
        assert len(matches) == 1
        assert matches[0].group(1).startswith("lsv2_sk_")

    def test_personal_token_pattern(self, provider: LangSmithProvider) -> None:
        """Personal token lsv2_pt_ is detected."""
        key = "lsv2_pt_" + "b" * 32
        text = f"LANGCHAIN_API_KEY={key}"
        matches = provider.match(text)
        assert len(matches) == 1
        assert matches[0].group(1).startswith("lsv2_pt_")

    def test_longer_key(self, provider: LangSmithProvider) -> None:
        """Longer key is detected."""
        key = "lsv2_sk_" + "c" * 48
        text = f'token = "{key}"'
        matches = provider.match(text)
        assert len(matches) == 1

    def test_short_key_not_matched(self, provider: LangSmithProvider) -> None:
        """Key shorter than 32 chars after prefix is not matched."""
        key = "lsv2_sk_" + "d" * 20  # Only 20 chars after prefix
        text = f"api_key = '{key}'"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_wrong_prefix_not_matched(self, provider: LangSmithProvider) -> None:
        """Key without lsv2_ prefix is not matched."""
        key = "lsv1_sk_" + "e" * 32
        text = f"api_key = '{key}'"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_wrong_type_not_matched(self, provider: LangSmithProvider) -> None:
        """Key with wrong type (not sk or pt) is not matched."""
        key = "lsv2_xx_" + "f" * 32
        text = f"api_key = '{key}'"
        matches = provider.match(text)
        assert len(matches) == 0


class TestLangSmithProviderAuth:
    """Tests for LangSmith provider authentication."""

    def test_build_auth_header(self) -> None:
        """Auth header uses x-api-key."""
        provider = LangSmithProvider()
        key = "lsv2_sk_" + "g" * 32
        header = provider.build_auth_header(key)

        assert header == {"x-api-key": key}


class TestLangSmithProviderInterpretResponse:
    """Tests for LangSmith provider response interpretation."""

    @pytest.fixture
    def provider(self) -> LangSmithProvider:
        """Create provider instance."""
        return LangSmithProvider()

    def test_200_valid(self, provider: LangSmithProvider) -> None:
        """200 response indicates valid key."""
        result = provider.interpret_response(200, {"sessions": []})
        assert result.status == ValidationStatus.VALID

    def test_401_invalid(self, provider: LangSmithProvider) -> None:
        """401 response indicates invalid key."""
        result = provider.interpret_response(401, {"error": "Unauthorized"})
        assert result.status == ValidationStatus.INVALID

    def test_403_valid_but_no_permission(self, provider: LangSmithProvider) -> None:
        """403 response indicates valid key with limited permissions."""
        result = provider.interpret_response(403, None)
        assert result.status == ValidationStatus.VALID  # Key is valid but lacks perms

    def test_429_rate_limited(self, provider: LangSmithProvider) -> None:
        """429 response indicates rate limit."""
        result = provider.interpret_response(429, None)
        assert result.status == ValidationStatus.RATE_LIMITED

    def test_500_server_error(self, provider: LangSmithProvider) -> None:
        """500 response indicates server error."""
        result = provider.interpret_response(500, None)
        assert result.status == ValidationStatus.ERROR
