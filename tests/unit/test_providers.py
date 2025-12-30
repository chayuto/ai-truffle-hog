"""Unit tests for provider base and registry."""

import re
from pathlib import Path
from typing import Optional

import pytest

from ai_truffle_hog.providers.base import BaseProvider, ValidationResult, ValidationStatus
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
    def patterns(self) -> dict[str, re.Pattern[str]]:
        return {
            "api_key": re.compile(r"mock-[a-z0-9]{16}"),
        }

    async def validate_key(self, key: str, key_type: str) -> ValidationResult:
        if key == "mock-validkey12345678":
            return ValidationResult(
                status=ValidationStatus.VALID,
                message="Key is valid",
            )
        return ValidationResult(
            status=ValidationStatus.INVALID,
            message="Key is invalid",
        )

    def get_auth_header(self, key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {key}"}


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
        assert "api_key" in patterns
        assert hasattr(patterns["api_key"], "match")

    def test_pattern_matching(self) -> None:
        """Pattern matches expected format."""
        provider = MockProvider()
        pattern = provider.patterns["api_key"]

        assert pattern.search("mock-abcd1234efgh5678")
        assert not pattern.search("other-key-format")

    def test_get_auth_header(self) -> None:
        """Auth header is formatted correctly."""
        provider = MockProvider()
        header = provider.get_auth_header("test-key")
        assert header == {"Authorization": "Bearer test-key"}


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
            message="Active key",
            metadata={"org": "test-org", "rate_limit": 1000},
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

        assert "mock" in registry.list_providers()
        assert registry.get("mock") is provider

    def test_get_unknown_provider(self) -> None:
        """Get unknown provider returns None."""
        registry = ProviderRegistry()
        assert registry.get("unknown") is None

    def test_list_providers(self) -> None:
        """List registered providers."""
        registry = ProviderRegistry()
        registry.register(MockProvider())

        providers = registry.list_providers()
        assert "mock" in providers

    def test_get_all_patterns(self) -> None:
        """Get patterns from all providers."""
        registry = ProviderRegistry()
        registry.register(MockProvider())

        patterns = registry.get_all_patterns()
        assert ("mock", "api_key") in [(p, t) for p, t, _ in patterns]


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
