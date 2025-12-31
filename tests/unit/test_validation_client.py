"""Unit tests for ValidationClient module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from ai_truffle_hog.providers.base import ValidationResult, ValidationStatus
from ai_truffle_hog.validator.client import (
    SecretCandidate,
    ValidationClient,
    ValidationClientConfig,
    ValidationStats,
    create_validation_client,
)


class TestSecretCandidate:
    """Tests for SecretCandidate dataclass."""

    def test_creation(self) -> None:
        """Test creating SecretCandidate."""
        candidate = SecretCandidate(
            provider_name="openai",
            secret_value="sk-test123",
            file_path="config.py",
            line_number=10,
        )

        assert candidate.provider_name == "openai"
        assert candidate.secret_value == "sk-test123"
        assert candidate.file_path == "config.py"
        assert candidate.line_number == 10
        assert candidate.validation_result is None

    def test_is_validated_false(self) -> None:
        """Test is_validated is False initially."""
        candidate = SecretCandidate(
            provider_name="openai",
            secret_value="sk-test123",
        )
        assert not candidate.is_validated

    def test_is_validated_true(self) -> None:
        """Test is_validated is True after validation."""
        candidate = SecretCandidate(
            provider_name="openai",
            secret_value="sk-test123",
        )
        candidate.validation_result = ValidationResult(status=ValidationStatus.VALID)
        assert candidate.is_validated

    def test_is_valid_true(self) -> None:
        """Test is_valid returns True for valid keys."""
        candidate = SecretCandidate(
            provider_name="openai",
            secret_value="sk-test123",
        )
        candidate.validation_result = ValidationResult(status=ValidationStatus.VALID)
        assert candidate.is_valid

    def test_is_valid_false_invalid(self) -> None:
        """Test is_valid returns False for invalid keys."""
        candidate = SecretCandidate(
            provider_name="openai",
            secret_value="sk-test123",
        )
        candidate.validation_result = ValidationResult(status=ValidationStatus.INVALID)
        assert not candidate.is_valid

    def test_is_valid_false_not_validated(self) -> None:
        """Test is_valid returns False if not validated."""
        candidate = SecretCandidate(
            provider_name="openai",
            secret_value="sk-test123",
        )
        assert not candidate.is_valid


class TestValidationStats:
    """Tests for ValidationStats dataclass."""

    def test_initial_values(self) -> None:
        """Test initial stat values are zero."""
        stats = ValidationStats()
        assert stats.total == 0
        assert stats.validated == 0
        assert stats.valid == 0
        assert stats.invalid == 0
        assert stats.errors == 0
        assert stats.skipped == 0

    def test_add_valid_result(self) -> None:
        """Test adding valid result."""
        stats = ValidationStats(total=1)
        result = ValidationResult(status=ValidationStatus.VALID)
        stats.add_result(result)
        assert stats.validated == 1
        assert stats.valid == 1

    def test_add_invalid_result(self) -> None:
        """Test adding invalid result."""
        stats = ValidationStats(total=1)
        result = ValidationResult(status=ValidationStatus.INVALID)
        stats.add_result(result)
        assert stats.validated == 1
        assert stats.invalid == 1

    def test_add_error_result(self) -> None:
        """Test adding error result."""
        stats = ValidationStats(total=1)
        result = ValidationResult(status=ValidationStatus.ERROR)
        stats.add_result(result)
        assert stats.validated == 1
        assert stats.errors == 1

    def test_add_skipped_result(self) -> None:
        """Test adding skipped result."""
        stats = ValidationStats(total=1)
        result = ValidationResult(status=ValidationStatus.SKIPPED)
        stats.add_result(result)
        assert stats.validated == 1
        assert stats.skipped == 1


class TestValidationClientConfig:
    """Tests for ValidationClientConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ValidationClientConfig()
        assert config.timeout == 10.0
        assert config.max_concurrent == 5
        assert not config.skip_validation
        assert config.retry_on_rate_limit
        assert config.max_retries == 3

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ValidationClientConfig(
            timeout=30.0,
            max_concurrent=10,
            skip_validation=True,
        )
        assert config.timeout == 30.0
        assert config.max_concurrent == 10
        assert config.skip_validation


class TestValidationClient:
    """Tests for ValidationClient class."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        client = ValidationClient()
        assert client.config is not None
        assert not client.is_open

    def test_init_with_config(self) -> None:
        """Test initialization with config."""
        config = ValidationClientConfig(timeout=20.0)
        client = ValidationClient(config=config)
        assert client.config.timeout == 20.0

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test async context manager."""
        async with ValidationClient() as client:
            assert client.is_open
        assert not client.is_open

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        """Test closing the client."""
        client = ValidationClient()
        await client._ensure_client()
        assert client.is_open
        await client.close()
        assert not client.is_open

    @pytest.mark.asyncio
    async def test_validate_key_skip_validation(self) -> None:
        """Test validation is skipped when configured."""
        config = ValidationClientConfig(skip_validation=True)
        client = ValidationClient(config=config)

        mock_provider = MagicMock()
        mock_provider.name = "test"

        result = await client.validate_key(mock_provider, "test-key")

        assert result.status == ValidationStatus.SKIPPED
        assert "skipped" in result.message.lower()

    @pytest.mark.asyncio
    async def test_validate_key_timeout(self) -> None:
        """Test handling of timeout errors."""
        async with ValidationClient() as client:
            mock_provider = MagicMock()
            mock_provider.name = "test"
            mock_provider.validation_endpoint = "https://api.test.com/validate"
            mock_provider.build_auth_header.return_value = {"Authorization": "Bearer x"}

            with patch.object(
                client._client,
                "get",
                side_effect=httpx.TimeoutException("timeout"),
            ):
                result = await client.validate_key(mock_provider, "test-key")

            assert result.status == ValidationStatus.ERROR
            assert "timed out" in result.message.lower()

    @pytest.mark.asyncio
    async def test_validate_key_request_error(self) -> None:
        """Test handling of request errors."""
        async with ValidationClient() as client:
            mock_provider = MagicMock()
            mock_provider.name = "test"
            mock_provider.validation_endpoint = "https://api.test.com/validate"
            mock_provider.build_auth_header.return_value = {"Authorization": "Bearer x"}

            with patch.object(
                client._client,
                "get",
                side_effect=httpx.RequestError("connection failed"),
            ):
                result = await client.validate_key(mock_provider, "test-key")

            assert result.status == ValidationStatus.ERROR
            assert "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_validate_key_success(self) -> None:
        """Test successful validation."""
        async with ValidationClient() as client:
            mock_provider = MagicMock()
            mock_provider.name = "test"
            mock_provider.validation_endpoint = "https://api.test.com/validate"
            mock_provider.build_auth_header.return_value = {"Authorization": "Bearer x"}
            mock_provider.interpret_response.return_value = ValidationResult(
                status=ValidationStatus.VALID
            )

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}

            with patch.object(
                client._client,
                "get",
                return_value=mock_response,
            ):
                result = await client.validate_key(mock_provider, "valid-key")

            assert result.status == ValidationStatus.VALID


class TestValidationClientBatch:
    """Tests for batch validation."""

    @pytest.mark.asyncio
    async def test_validate_batch_empty(self) -> None:
        """Test validating empty batch."""
        async with ValidationClient() as client:
            candidates, stats = await client.validate_batch([])

        assert candidates == []
        assert stats.total == 0

    @pytest.mark.asyncio
    async def test_validate_batch_unknown_provider(self) -> None:
        """Test batch with unknown provider."""
        async with ValidationClient() as client:
            candidates = [
                SecretCandidate(
                    provider_name="unknown_provider_xyz",
                    secret_value="test-key",
                )
            ]

            results, _stats = await client.validate_batch(candidates)

        assert len(results) == 1
        assert results[0].validation_result is not None
        assert results[0].validation_result.status == ValidationStatus.ERROR
        assert "Unknown provider" in results[0].validation_result.message

    @pytest.mark.asyncio
    async def test_validate_by_provider_unknown(self) -> None:
        """Test validating by unknown provider."""
        async with ValidationClient() as client:
            results = await client.validate_by_provider(
                "unknown_provider_xyz",
                ["key1", "key2"],
            )

        assert len(results) == 2
        assert all(r.status == ValidationStatus.ERROR for r in results)


class TestCreateValidationClient:
    """Tests for create_validation_client factory function."""

    def test_create_default(self) -> None:
        """Test creating default client."""
        client = create_validation_client()
        assert isinstance(client, ValidationClient)
        assert client.config.timeout == 10.0

    def test_create_with_options(self) -> None:
        """Test creating with custom options."""
        client = create_validation_client(
            timeout=30.0,
            max_concurrent=10,
            skip_validation=True,
        )

        assert client.config.timeout == 30.0
        assert client.config.max_concurrent == 10
        assert client.config.skip_validation
