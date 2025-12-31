"""Unit tests for Google Gemini provider implementation."""

import pytest

from ai_truffle_hog.providers.base import ValidationStatus
from ai_truffle_hog.providers.google import GoogleGeminiProvider


class TestGoogleGeminiProviderProperties:
    """Tests for Google Gemini provider properties."""

    def test_name(self) -> None:
        """Provider name is correct."""
        provider = GoogleGeminiProvider()
        assert provider.name == "google_gemini"

    def test_display_name(self) -> None:
        """Display name is correct."""
        provider = GoogleGeminiProvider()
        assert provider.display_name == "Google Gemini"

    def test_validation_endpoint(self) -> None:
        """Validation endpoint is correct."""
        provider = GoogleGeminiProvider()
        assert "generativelanguage.googleapis.com" in provider.validation_endpoint

    def test_auth_header_name(self) -> None:
        """Auth header name is empty (uses query param)."""
        provider = GoogleGeminiProvider()
        assert provider.auth_header_name == ""

    def test_patterns_count(self) -> None:
        """Provider has expected number of patterns."""
        provider = GoogleGeminiProvider()
        assert len(provider.patterns) == 1


class TestGoogleGeminiProviderPatterns:
    """Tests for Google Gemini key pattern matching."""

    @pytest.fixture
    def provider(self) -> GoogleGeminiProvider:
        """Create provider instance."""
        return GoogleGeminiProvider()

    def test_aiza_key_pattern(self, provider: GoogleGeminiProvider) -> None:
        """AIza prefixed key is detected."""
        # AIza + 35 chars = 39 total
        text = "api_key = 'AIzaSyC1234567890abcdefghijklmnopqrstuv'"
        matches = provider.match(text)
        assert len(matches) == 1
        assert matches[0].group(1).startswith("AIza")

    def test_key_in_env_var(self, provider: GoogleGeminiProvider) -> None:
        """Key in environment variable is detected."""
        # AIza + 35 chars = 39 total
        key39 = "AIza" + "x" * 35
        text = f"GOOGLE_API_KEY={key39}"
        matches = provider.match(text)
        assert len(matches) == 1

    def test_key_with_special_chars(self, provider: GoogleGeminiProvider) -> None:
        """Key with dash and underscore is detected."""
        text = 'key = "AIzaSyE-abcd_EFGH-ijkl_MNOP-qrst_UVWX-y"'
        matches = provider.match(text)
        assert len(matches) == 1

    def test_key_in_url(self, provider: GoogleGeminiProvider) -> None:
        """Key in URL query parameter is detected."""
        # AIza + 35 chars = 39 total
        key39 = "AIza" + "y" * 35
        text = f"https://api.google.com?key={key39}"
        matches = provider.match(text)
        assert len(matches) == 1

    def test_short_key_not_matched(self, provider: GoogleGeminiProvider) -> None:
        """Key shorter than expected is not matched."""
        text = "AIzaSyGtooshort123"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_wrong_prefix_not_matched(self, provider: GoogleGeminiProvider) -> None:
        """Key without AIza prefix is not matched."""
        text = "BIza1234567890abcdefghijklmnopqrstuvwxyz"
        matches = provider.match(text)
        assert len(matches) == 0


class TestGoogleGeminiProviderAuth:
    """Tests for Google Gemini provider authentication."""

    def test_build_auth_header_empty(self) -> None:
        """Auth header is empty (uses query param instead)."""
        provider = GoogleGeminiProvider()
        key = "AIzaSyH1234567890abcdefghijklmnopqrstuv"
        header = provider.build_auth_header(key)

        assert header == {}

    def test_build_validation_url(self) -> None:
        """Validation URL includes key as query param."""
        provider = GoogleGeminiProvider()
        key = "AIzaSyI1234567890abcdefghijklmnopqrstuv"
        url = provider.build_validation_url(key)

        assert provider.validation_endpoint in url
        assert f"key={key}" in url


class TestGoogleGeminiProviderInterpretResponse:
    """Tests for Google Gemini provider response interpretation."""

    @pytest.fixture
    def provider(self) -> GoogleGeminiProvider:
        """Create provider instance."""
        return GoogleGeminiProvider()

    def test_200_valid(self, provider: GoogleGeminiProvider) -> None:
        """200 response indicates valid key."""
        result = provider.interpret_response(200, {"models": []})
        assert result.status == ValidationStatus.VALID

    def test_400_invalid(self, provider: GoogleGeminiProvider) -> None:
        """400 response indicates invalid key."""
        result = provider.interpret_response(400, {"error": "Invalid key"})
        assert result.status == ValidationStatus.INVALID

    def test_403_invalid(self, provider: GoogleGeminiProvider) -> None:
        """403 response indicates invalid or not authorized."""
        result = provider.interpret_response(403, None)
        assert result.status == ValidationStatus.INVALID

    def test_429_quota_exceeded(self, provider: GoogleGeminiProvider) -> None:
        """429 response indicates quota exceeded."""
        result = provider.interpret_response(429, None)
        assert result.status == ValidationStatus.QUOTA_EXCEEDED

    def test_500_server_error(self, provider: GoogleGeminiProvider) -> None:
        """500 response indicates server error."""
        result = provider.interpret_response(500, None)
        assert result.status == ValidationStatus.ERROR
