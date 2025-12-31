"""Unit tests for Replicate provider implementation."""

import pytest

from ai_truffle_hog.providers.base import ValidationStatus
from ai_truffle_hog.providers.replicate import ReplicateProvider


class TestReplicateProviderProperties:
    """Tests for Replicate provider properties."""

    def test_name(self) -> None:
        """Provider name is correct."""
        provider = ReplicateProvider()
        assert provider.name == "replicate"

    def test_display_name(self) -> None:
        """Display name is correct."""
        provider = ReplicateProvider()
        assert provider.display_name == "Replicate"

    def test_validation_endpoint(self) -> None:
        """Validation endpoint is correct."""
        provider = ReplicateProvider()
        assert provider.validation_endpoint == "https://api.replicate.com/v1/account"

    def test_auth_header_name(self) -> None:
        """Auth header name is correct."""
        provider = ReplicateProvider()
        assert provider.auth_header_name == "Authorization"

    def test_patterns_count(self) -> None:
        """Provider has expected number of patterns."""
        provider = ReplicateProvider()
        assert len(provider.patterns) == 1


class TestReplicateProviderPatterns:
    """Tests for Replicate token pattern matching."""

    @pytest.fixture
    def provider(self) -> ReplicateProvider:
        """Create provider instance."""
        return ReplicateProvider()

    def test_standard_token_pattern(self, provider: ReplicateProvider) -> None:
        """Standard r8_ token is detected (37 chars after prefix)."""
        # r8_ + 37 alphanumeric = 40 total
        text = "api_key = 'r8_abcdefghijklmnopqrstuvwxyz1234567890a'"
        matches = provider.match(text)
        assert len(matches) == 1
        assert matches[0].group(1).startswith("r8_")

    def test_token_in_env_var(self, provider: ReplicateProvider) -> None:
        """Token in environment variable is detected."""
        text = "REPLICATE_API_TOKEN=r8_abcdefghijklmnopqrstuvwxyz1234567890a"
        matches = provider.match(text)
        assert len(matches) == 1

    def test_token_in_code(self, provider: ReplicateProvider) -> None:
        """Token in Python code is detected."""
        text = 'token = "r8_abcdefghijklmnopqrstuvwxyz1234567890a"'
        matches = provider.match(text)
        assert len(matches) == 1

    def test_short_token_not_matched(self, provider: ReplicateProvider) -> None:
        """Token shorter than expected is not matched."""
        text = "r8_tooshort123"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_wrong_prefix_not_matched(self, provider: ReplicateProvider) -> None:
        """Token without r8_ prefix is not matched."""
        text = "r9_1234567890abcdefghijklmnopqrstuvwxyz12"
        matches = provider.match(text)
        assert len(matches) == 0

    def test_multiple_tokens_detected(self, provider: ReplicateProvider) -> None:
        """Multiple tokens are detected in same text."""
        text = """
        token1 = "r8_abcdefghijklmnopqrstuvwxyz1234567890a"
        token2 = "r8_ABCDEFGHIJKLMNOPQRSTUVWXYZ9876543210b"
        """
        matches = provider.match(text)
        assert len(matches) == 2


class TestReplicateProviderAuth:
    """Tests for Replicate provider authentication."""

    def test_build_auth_header(self) -> None:
        """Auth header is formatted correctly."""
        provider = ReplicateProvider()
        key = "r8_abcdefghijklmnopqrstuvwxyz1234567890a"
        header = provider.build_auth_header(key)

        assert header == {"Authorization": f"Bearer {key}"}


class TestReplicateProviderInterpretResponse:
    """Tests for Replicate provider response interpretation."""

    @pytest.fixture
    def provider(self) -> ReplicateProvider:
        """Create provider instance."""
        return ReplicateProvider()

    def test_200_valid_with_metadata(self, provider: ReplicateProvider) -> None:
        """200 response with account info returns metadata."""
        body = {"username": "testuser", "type": "personal"}
        result = provider.interpret_response(200, body)
        assert result.status == ValidationStatus.VALID
        assert result.metadata is not None
        assert result.metadata.get("username") == "testuser"

    def test_200_valid_without_metadata(self, provider: ReplicateProvider) -> None:
        """200 response without details still valid."""
        result = provider.interpret_response(200, {})
        assert result.status == ValidationStatus.VALID

    def test_401_invalid(self, provider: ReplicateProvider) -> None:
        """401 response indicates invalid token."""
        result = provider.interpret_response(401, {"detail": "Unauthorized"})
        assert result.status == ValidationStatus.INVALID

    def test_429_rate_limited(self, provider: ReplicateProvider) -> None:
        """429 response indicates rate limit."""
        result = provider.interpret_response(429, None)
        assert result.status == ValidationStatus.RATE_LIMITED

    def test_500_server_error(self, provider: ReplicateProvider) -> None:
        """500 response indicates server error."""
        result = provider.interpret_response(500, None)
        assert result.status == ValidationStatus.ERROR
