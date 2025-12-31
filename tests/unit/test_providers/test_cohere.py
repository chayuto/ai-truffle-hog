"""Unit tests for Cohere provider implementation."""

import pytest

from ai_truffle_hog.providers.base import ValidationStatus
from ai_truffle_hog.providers.cohere import CohereProvider


class TestCohereProviderProperties:
    """Tests for Cohere provider properties."""

    def test_name(self) -> None:
        """Provider name is correct."""
        provider = CohereProvider()
        assert provider.name == "cohere"

    def test_display_name(self) -> None:
        """Display name is correct."""
        provider = CohereProvider()
        assert provider.display_name == "Cohere"

    def test_validation_endpoint(self) -> None:
        """Validation endpoint is correct."""
        provider = CohereProvider()
        assert provider.validation_endpoint == "https://api.cohere.ai/v1/check-api-key"

    def test_auth_header_name(self) -> None:
        """Auth header name is correct."""
        provider = CohereProvider()
        assert provider.auth_header_name == "Authorization"

    def test_patterns_count(self) -> None:
        """Provider has expected number of patterns."""
        provider = CohereProvider()
        assert len(provider.patterns) == 2


class TestCohereProviderPatterns:
    """Tests for Cohere key pattern matching."""

    @pytest.fixture
    def provider(self) -> CohereProvider:
        """Create provider instance."""
        return CohereProvider()

    def test_contextual_key_pattern(self, provider: CohereProvider) -> None:
        """Key with 'cohere' context is detected."""
        # Cohere keys must be exactly 40 alphanumeric characters
        key40 = "a" * 40
        text = f"cohere_key = '{key40}'"
        matches = provider.match(text)
        assert len(matches) == 1
        assert len(matches[0].group(1)) == 40

    def test_env_var_pattern(self, provider: CohereProvider) -> None:
        """COHERE_API_KEY environment variable is detected."""
        key40 = "b" * 40
        text = f"COHERE_API_KEY={key40}"
        matches = provider.match(text)
        assert len(matches) == 1

    def test_env_var_with_quotes(self, provider: CohereProvider) -> None:
        """COHERE_API_KEY with quotes is detected."""
        key40 = "c" * 40
        text = f'COHERE_API_KEY="{key40}"'
        matches = provider.match(text)
        # Both contextual and env var patterns may match
        assert len(matches) >= 1

    def test_cohere_in_variable_name(self, provider: CohereProvider) -> None:
        """Key with cohere in variable name is detected."""
        key40 = "d" * 40
        text = f'my_cohere_key = "{key40}"'
        matches = provider.match(text)
        assert len(matches) == 1

    def test_wrong_length_not_matched(self, provider: CohereProvider) -> None:
        """Key with wrong length (not 40) is not matched."""
        text = "COHERE_API_KEY=tooshort123"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_no_context_not_matched(self, provider: CohereProvider) -> None:
        """Key without cohere context is not matched."""
        # This is 40 chars but no 'cohere' context
        text = "api_key = 'abcdefghijklmnopqrstuvwxyz1234567890ab'"
        matches = provider.match(text)
        assert len(matches) == 0


class TestCohereProviderAuth:
    """Tests for Cohere provider authentication."""

    def test_build_auth_header(self) -> None:
        """Auth header is formatted correctly."""
        provider = CohereProvider()
        key = "abcdefghijklmnopqrstuvwxyz1234567890ab"
        header = provider.build_auth_header(key)

        assert header["Authorization"] == f"Bearer {key}"
        assert header["Content-Type"] == "application/json"

    def test_validation_body(self) -> None:
        """Validation body is empty."""
        provider = CohereProvider()
        body = provider.get_validation_body()
        assert body == {}


class TestCohereProviderInterpretResponse:
    """Tests for Cohere provider response interpretation."""

    @pytest.fixture
    def provider(self) -> CohereProvider:
        """Create provider instance."""
        return CohereProvider()

    def test_200_valid_true(self, provider: CohereProvider) -> None:
        """200 response with valid=true indicates valid key."""
        result = provider.interpret_response(200, {"valid": True})
        assert result.status == ValidationStatus.VALID

    def test_200_valid_false(self, provider: CohereProvider) -> None:
        """200 response with valid=false indicates invalid key."""
        result = provider.interpret_response(200, {"valid": False})
        assert result.status == ValidationStatus.INVALID

    def test_200_no_valid_field(self, provider: CohereProvider) -> None:
        """200 response without valid field indicates invalid."""
        result = provider.interpret_response(200, {})
        assert result.status == ValidationStatus.INVALID

    def test_401_invalid(self, provider: CohereProvider) -> None:
        """401 response indicates invalid key."""
        result = provider.interpret_response(401, {"error": "Unauthorized"})
        assert result.status == ValidationStatus.INVALID

    def test_429_rate_limited(self, provider: CohereProvider) -> None:
        """429 response indicates rate limit."""
        result = provider.interpret_response(429, None)
        assert result.status == ValidationStatus.RATE_LIMITED

    def test_500_server_error(self, provider: CohereProvider) -> None:
        """500 response indicates server error."""
        result = provider.interpret_response(500, None)
        assert result.status == ValidationStatus.ERROR
