"""Unit tests for provider base and registry."""

import re

from ai_truffle_hog.providers.base import (
    BaseProvider,
    ValidationResult,
    ValidationStatus,
)
from ai_truffle_hog.providers.registry import ProviderRegistry, get_registry


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def display_name(self) -> str:
        return "Mock Provider"

    @property
    def patterns(self) -> list[re.Pattern[str]]:
        return [re.compile(r"mock-[a-z0-9]{16}")]

    @property
    def validation_endpoint(self) -> str:
        return "https://api.mock.com/v1/validate"

    @property
    def auth_header_name(self) -> str:
        return "Authorization"

    def build_auth_header(self, key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {key}"}

    def interpret_response(
        self,
        status_code: int,
        response_body: dict[str, object] | None,
    ) -> ValidationResult:
        if status_code == 200:
            return ValidationResult(
                status=ValidationStatus.VALID,
                http_status_code=status_code,
                message="Key is valid",
            )
        return ValidationResult(
            status=ValidationStatus.INVALID,
            http_status_code=status_code,
            message="Key is invalid",
        )


class TestBaseProvider:
    """Tests for BaseProvider ABC."""

    def test_mock_provider_name(self) -> None:
        """Provider name is correct."""
        provider = MockProvider()
        assert provider.name == "mock"
        assert provider.display_name == "Mock Provider"

    def test_patterns_are_regex(self) -> None:
        """Patterns are compiled regex."""
        provider = MockProvider()
        patterns = provider.patterns
        assert len(patterns) == 1
        assert hasattr(patterns[0], "match")

    def test_pattern_matching(self) -> None:
        """Pattern matches expected format."""
        provider = MockProvider()
        pattern = provider.patterns[0]

        assert pattern.search("mock-abcd1234efgh5678")
        assert not pattern.search("other-key-format")

    def test_build_auth_header(self) -> None:
        """Auth header is formatted correctly."""
        provider = MockProvider()
        header = provider.build_auth_header("test-key")
        assert header == {"Authorization": "Bearer test-key"}

    def test_match_method(self) -> None:
        """match() method returns matches."""
        provider = MockProvider()
        text = "Key: mock-abcd1234efgh5678 and mock-1234567890abcdef"
        matches = provider.match(text)
        assert len(matches) == 2


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_creation(self) -> None:
        """Create ValidationResult."""
        result = ValidationResult(
            status=ValidationStatus.VALID,
            message="Success",
        )
        assert result.status == ValidationStatus.VALID
        assert result.message == "Success"

    def test_with_metadata(self) -> None:
        """ValidationResult with metadata."""
        result = ValidationResult(
            status=ValidationStatus.VALID,
            http_status_code=200,
            message="Active key",
            metadata={"org": "test-org", "rate_limit": "1000"},
        )
        assert result.metadata is not None
        assert result.metadata["org"] == "test-org"


class TestProviderRegistry:
    """Tests for ProviderRegistry."""

    def test_register_provider(self) -> None:
        """Register a provider."""
        registry = ProviderRegistry()
        provider = MockProvider()

        registry.register(provider)

        assert "mock" in registry.names()
        assert registry.get("mock") is provider

    def test_get_unknown_provider(self) -> None:
        """Get unknown provider returns None."""
        registry = ProviderRegistry()
        assert registry.get("unknown") is None

    def test_list_providers(self) -> None:
        """List registered providers."""
        registry = ProviderRegistry()
        registry.register(MockProvider())

        names = registry.names()
        assert "mock" in names

    def test_all_providers(self) -> None:
        """Get all providers."""
        registry = ProviderRegistry()
        registry.register(MockProvider())

        providers = registry.all()
        assert len(providers) == 1
        assert providers[0].name == "mock"


class TestGetRegistry:
    """Tests for get_registry singleton."""

    def test_returns_registry(self) -> None:
        """get_registry returns a ProviderRegistry."""
        registry = get_registry()
        assert isinstance(registry, ProviderRegistry)

    def test_singleton_pattern(self) -> None:
        """get_registry returns same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2
