"""Unit tests for provider registry with all providers."""

import pytest

from ai_truffle_hog.providers import (
    AnthropicProvider,
    CohereProvider,
    GoogleGeminiProvider,
    GroqProvider,
    HuggingFaceProvider,
    LangSmithProvider,
    OpenAIProvider,
    ReplicateProvider,
    get_registry,
)


class TestRegistryWithAllProviders:
    """Tests for registry with all provider implementations."""

    def test_all_providers_registered(self) -> None:
        """All 8 providers are registered."""
        registry = get_registry()
        assert len(registry) == 8

    def test_provider_names(self) -> None:
        """All expected provider names are present."""
        registry = get_registry()
        expected_names = {
            "openai",
            "anthropic",
            "huggingface",
            "cohere",
            "replicate",
            "google_gemini",
            "groq",
            "langsmith",
        }
        actual_names = set(registry.names())
        assert expected_names == actual_names

    def test_get_openai(self) -> None:
        """Can retrieve OpenAI provider."""
        registry = get_registry()
        provider = registry.get("openai")
        assert provider is not None
        assert isinstance(provider, OpenAIProvider)

    def test_get_anthropic(self) -> None:
        """Can retrieve Anthropic provider."""
        registry = get_registry()
        provider = registry.get("anthropic")
        assert provider is not None
        assert isinstance(provider, AnthropicProvider)

    def test_get_huggingface(self) -> None:
        """Can retrieve Hugging Face provider."""
        registry = get_registry()
        provider = registry.get("huggingface")
        assert provider is not None
        assert isinstance(provider, HuggingFaceProvider)

    def test_get_cohere(self) -> None:
        """Can retrieve Cohere provider."""
        registry = get_registry()
        provider = registry.get("cohere")
        assert provider is not None
        assert isinstance(provider, CohereProvider)

    def test_get_replicate(self) -> None:
        """Can retrieve Replicate provider."""
        registry = get_registry()
        provider = registry.get("replicate")
        assert provider is not None
        assert isinstance(provider, ReplicateProvider)

    def test_get_google_gemini(self) -> None:
        """Can retrieve Google Gemini provider."""
        registry = get_registry()
        provider = registry.get("google_gemini")
        assert provider is not None
        assert isinstance(provider, GoogleGeminiProvider)

    def test_get_groq(self) -> None:
        """Can retrieve Groq provider."""
        registry = get_registry()
        provider = registry.get("groq")
        assert provider is not None
        assert isinstance(provider, GroqProvider)

    def test_get_langsmith(self) -> None:
        """Can retrieve LangSmith provider."""
        registry = get_registry()
        provider = registry.get("langsmith")
        assert provider is not None
        assert isinstance(provider, LangSmithProvider)


class TestProviderPatternUniqueness:
    """Tests to ensure provider patterns don't conflict."""

    @pytest.fixture
    def all_providers(self) -> list:
        """Get all provider instances."""
        return [
            OpenAIProvider(),
            AnthropicProvider(),
            HuggingFaceProvider(),
            CohereProvider(),
            ReplicateProvider(),
            GoogleGeminiProvider(),
            GroqProvider(),
            LangSmithProvider(),
        ]

    def test_openai_pattern_unique(self, all_providers: list) -> None:
        """OpenAI pattern doesn't match other providers."""
        test_key = "sk-proj-abc123def456ghi789jkl012mno345"
        for provider in all_providers:
            matches = provider.match(test_key)
            if provider.name == "openai":
                assert len(matches) == 1
            else:
                # Other providers shouldn't match OpenAI keys
                assert len(matches) == 0, f"{provider.name} matched OpenAI key"

    def test_anthropic_pattern_unique(self, all_providers: list) -> None:
        """Anthropic pattern doesn't match other providers."""
        # Anthropic API keys need 80-120 chars after the prefix
        key_suffix = "a" * 85
        test_key = f"sk-ant-api03-{key_suffix}"
        for provider in all_providers:
            matches = provider.match(test_key)
            if provider.name == "anthropic":
                assert len(matches) == 1
            else:
                assert len(matches) == 0, f"{provider.name} matched Anthropic key"

    def test_huggingface_pattern_unique(self, all_providers: list) -> None:
        """Hugging Face pattern doesn't match other providers."""
        test_key = "hf_abcdefghijklmnopqrstuvwxyz12345678"
        for provider in all_providers:
            matches = provider.match(test_key)
            if provider.name == "huggingface":
                assert len(matches) == 1
            else:
                assert len(matches) == 0, f"{provider.name} matched HuggingFace key"

    def test_replicate_pattern_unique(self, all_providers: list) -> None:
        """Replicate pattern doesn't match other providers."""
        test_key = "r8_abcdefghijklmnopqrstuvwxyz1234567890a"
        for provider in all_providers:
            matches = provider.match(test_key)
            if provider.name == "replicate":
                assert len(matches) == 1
            else:
                assert len(matches) == 0, f"{provider.name} matched Replicate key"

    def test_google_pattern_unique(self, all_providers: list) -> None:
        """Google pattern doesn't match other providers."""
        test_key = "AIzaSyC1234567890abcdefghijklmnopqrstuv"
        for provider in all_providers:
            matches = provider.match(test_key)
            if provider.name == "google_gemini":
                assert len(matches) == 1
            else:
                assert len(matches) == 0, f"{provider.name} matched Google key"

    def test_groq_pattern_unique(self, all_providers: list) -> None:
        """Groq pattern doesn't match other providers."""
        test_key = "gsk_" + "a" * 52
        for provider in all_providers:
            matches = provider.match(test_key)
            if provider.name == "groq":
                assert len(matches) == 1
            else:
                assert len(matches) == 0, f"{provider.name} matched Groq key"

    def test_langsmith_pattern_unique(self, all_providers: list) -> None:
        """LangSmith pattern doesn't match other providers."""
        test_key = "lsv2_sk_" + "a" * 32
        for provider in all_providers:
            matches = provider.match(test_key)
            if provider.name == "langsmith":
                assert len(matches) == 1
            else:
                assert len(matches) == 0, f"{provider.name} matched LangSmith key"
