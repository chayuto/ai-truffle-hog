"""Provider registry for managing AI provider implementations.

This module provides a registry pattern for registering and retrieving
provider implementations at runtime.
"""

from typing import Optional

from ai_truffle_hog.providers.base import BaseProvider


class ProviderRegistry:
    """Registry for all supported AI providers.

    Provides methods to register, retrieve, and iterate over
    provider implementations.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._providers: dict[str, BaseProvider] = {}

    def register(self, provider: BaseProvider) -> None:
        """Register a provider instance.

        Args:
            provider: Provider instance to register.
        """
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[BaseProvider]:
        """Get a provider by name.

        Args:
            name: Provider identifier.

        Returns:
            Provider instance if found, None otherwise.
        """
        return self._providers.get(name)

    def all(self) -> list[BaseProvider]:
        """Get all registered providers.

        Returns:
            List of all provider instances.
        """
        return list(self._providers.values())

    def names(self) -> list[str]:
        """Get all provider names.

        Returns:
            List of registered provider identifiers.
        """
        return list(self._providers.keys())

    def __len__(self) -> int:
        """Return number of registered providers."""
        return len(self._providers)

    def __contains__(self, name: str) -> bool:
        """Check if provider is registered."""
        return name in self._providers


# Global registry instance
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Get the global provider registry.

    Initializes the registry with all providers on first access.

    Returns:
        The global ProviderRegistry instance.
    """
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
        _initialize_providers(_registry)
    return _registry


def _initialize_providers(registry: ProviderRegistry) -> None:
    """Initialize and register all providers.

    Args:
        registry: Registry to populate with providers.
    """
    # TODO: Import and register providers in Phase 3
    # from ai_truffle_hog.providers.openai import OpenAIProvider
    # from ai_truffle_hog.providers.anthropic import AnthropicProvider
    # etc.
    pass
