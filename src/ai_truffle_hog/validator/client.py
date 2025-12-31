"""Async validation client for API keys.

This module provides async HTTP client functionality for
validating discovered API keys against provider endpoints.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from ai_truffle_hog.providers.base import ValidationResult, ValidationStatus
from ai_truffle_hog.providers.registry import get_registry
from ai_truffle_hog.validator.rate_limiter import RateLimiter, create_rate_limiter

if TYPE_CHECKING:
    from ai_truffle_hog.providers.base import BaseProvider

logger = logging.getLogger(__name__)


@dataclass
class SecretCandidate:
    """A secret candidate for validation.

    Attributes:
        provider_name: Name of the provider (e.g., 'openai').
        secret_value: The actual secret value to validate.
        file_path: Where the secret was found.
        line_number: Line number in the file.
        validation_result: Result of validation (set after validate).
    """

    provider_name: str
    secret_value: str
    file_path: str = ""
    line_number: int = 0
    validation_result: ValidationResult | None = None

    @property
    def is_validated(self) -> bool:
        """Check if this candidate has been validated."""
        return self.validation_result is not None

    @property
    def is_valid(self) -> bool:
        """Check if this candidate is validated and valid."""
        return (
            self.validation_result is not None
            and self.validation_result.status == ValidationStatus.VALID
        )


@dataclass
class ValidationStats:
    """Statistics from a validation batch.

    Attributes:
        total: Total number of candidates.
        validated: Number successfully validated.
        valid: Number confirmed valid.
        invalid: Number confirmed invalid.
        errors: Number that failed with errors.
        skipped: Number skipped.
    """

    total: int = 0
    validated: int = 0
    valid: int = 0
    invalid: int = 0
    errors: int = 0
    skipped: int = 0

    def add_result(self, result: ValidationResult) -> None:
        """Update stats based on a validation result."""
        self.validated += 1
        match result.status:
            case ValidationStatus.VALID:
                self.valid += 1
            case ValidationStatus.INVALID:
                self.invalid += 1
            case ValidationStatus.ERROR:
                self.errors += 1
            case ValidationStatus.SKIPPED:
                self.skipped += 1
            case _:
                pass


@dataclass
class ValidationClientConfig:
    """Configuration for the validation client.

    Attributes:
        timeout: HTTP request timeout in seconds.
        max_concurrent: Maximum concurrent validations.
        skip_validation: If True, mark all as skipped without HTTP calls.
        retry_on_rate_limit: If True, retry after rate limit delay.
        max_retries: Maximum number of retries per request.
    """

    timeout: float = 10.0
    max_concurrent: int = 5
    skip_validation: bool = False
    retry_on_rate_limit: bool = True
    max_retries: int = 3


class ValidationClient:
    """Async HTTP client to validate API keys against provider endpoints.

    This client handles:
    - Async HTTP requests with proper timeout handling
    - Rate limiting per provider
    - Batch validation with concurrency limits
    - Error handling and retries

    Example:
        ```python
        async with ValidationClient() as client:
            result = await client.validate_key(provider, "sk-test123")
            print(f"Key is {result.status.value}")
        ```
    """

    def __init__(
        self,
        config: ValidationClientConfig | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initialize the validation client.

        Args:
            config: Client configuration.
            rate_limiter: Rate limiter instance.
        """
        self.config = config or ValidationClientConfig()
        self._rate_limiter = rate_limiter or create_rate_limiter()
        self._registry = get_registry()
        self._client: httpx.AsyncClient | None = None
        self._semaphore: asyncio.Semaphore | None = None

    @property
    def is_open(self) -> bool:
        """Check if the client is open and ready for requests."""
        return self._client is not None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is created."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True,
            )
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._semaphore = None

    async def __aenter__(self) -> ValidationClient:
        """Enter async context manager."""
        await self._ensure_client()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context manager."""
        await self.close()

    async def validate_key(
        self,
        provider: BaseProvider,
        key: str,
    ) -> ValidationResult:
        """Validate a single API key against a provider.

        Args:
            provider: The provider to validate against.
            key: The API key to validate.

        Returns:
            ValidationResult with the validation status.
        """
        if self.config.skip_validation:
            return ValidationResult(
                status=ValidationStatus.SKIPPED,
                message="Validation skipped by configuration",
            )

        client = await self._ensure_client()

        # Rate limiting
        await self._rate_limiter.acquire(provider.name)

        # Build request
        headers = provider.build_auth_header(key)
        endpoint = provider.validation_endpoint

        try:
            response = await client.get(endpoint, headers=headers)
            body: dict[str, object] | None = None
            with contextlib.suppress(Exception):
                body = response.json()

            return provider.interpret_response(response.status_code, body)

        except httpx.TimeoutException:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message="Request timed out",
            )
        except httpx.RequestError as e:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=f"Request failed: {e!s}",
            )
        except Exception as e:
            logger.exception("Unexpected error during validation")
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=f"Unexpected error: {e!s}",
            )

    async def _validate_with_retry(
        self,
        provider: BaseProvider,
        key: str,
    ) -> ValidationResult:
        """Validate a key with retry logic for rate limits.

        Args:
            provider: The provider to validate against.
            key: The API key to validate.

        Returns:
            ValidationResult with the validation status.
        """
        for attempt in range(self.config.max_retries):
            result = await self.validate_key(provider, key)

            # Retry on rate limit if configured
            if (
                result.status == ValidationStatus.RATE_LIMITED
                and self.config.retry_on_rate_limit
                and attempt < self.config.max_retries - 1
            ):
                # Exponential backoff
                wait_time = 2**attempt
                logger.debug(
                    "Rate limited by %s, retrying in %ds (attempt %d/%d)",
                    provider.name,
                    wait_time,
                    attempt + 1,
                    self.config.max_retries,
                )
                await asyncio.sleep(wait_time)
                continue

            return result

        return result  # Return last result after all retries

    async def _validate_candidate(
        self,
        candidate: SecretCandidate,
    ) -> SecretCandidate:
        """Validate a single secret candidate.

        Args:
            candidate: The candidate to validate.

        Returns:
            The candidate with validation_result set.
        """
        provider = self._registry.get(candidate.provider_name)
        if provider is None:
            candidate.validation_result = ValidationResult(
                status=ValidationStatus.ERROR,
                message=f"Unknown provider: {candidate.provider_name}",
            )
            return candidate

        # Use semaphore for concurrency limiting
        semaphore = self._semaphore or asyncio.Semaphore(self.config.max_concurrent)
        async with semaphore:
            result = await self._validate_with_retry(provider, candidate.secret_value)
            candidate.validation_result = result

        return candidate

    async def validate_batch(
        self,
        candidates: list[SecretCandidate],
    ) -> tuple[list[SecretCandidate], ValidationStats]:
        """Validate a batch of secret candidates.

        Args:
            candidates: List of candidates to validate.

        Returns:
            Tuple of (updated candidates, validation stats).
        """
        await self._ensure_client()

        stats = ValidationStats(total=len(candidates))

        if not candidates:
            return candidates, stats

        # Create tasks for all candidates
        tasks = [self._validate_candidate(c) for c in candidates]

        # Run all validations concurrently (semaphore limits concurrency)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and update stats
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                candidates[i].validation_result = ValidationResult(
                    status=ValidationStatus.ERROR,
                    message=str(result),
                )
                stats.errors += 1
            elif isinstance(result, SecretCandidate) and result.validation_result:
                stats.add_result(result.validation_result)

        return candidates, stats

    async def validate_by_provider(
        self,
        provider_name: str,
        keys: list[str],
    ) -> list[ValidationResult]:
        """Validate multiple keys for a single provider.

        Args:
            provider_name: Name of the provider.
            keys: List of keys to validate.

        Returns:
            List of validation results.
        """
        provider = self._registry.get(provider_name)
        if provider is None:
            return [
                ValidationResult(
                    status=ValidationStatus.ERROR,
                    message=f"Unknown provider: {provider_name}",
                )
                for _ in keys
            ]

        await self._ensure_client()

        async def validate_one(key: str) -> ValidationResult:
            semaphore = self._semaphore or asyncio.Semaphore(self.config.max_concurrent)
            async with semaphore:
                return await self._validate_with_retry(provider, key)

        return await asyncio.gather(*[validate_one(k) for k in keys])


def create_validation_client(
    timeout: float = 10.0,
    max_concurrent: int = 5,
    skip_validation: bool = False,
) -> ValidationClient:
    """Create a configured validation client.

    Args:
        timeout: HTTP request timeout in seconds.
        max_concurrent: Maximum concurrent validations.
        skip_validation: If True, skip actual HTTP validation.

    Returns:
        Configured ValidationClient instance.
    """
    config = ValidationClientConfig(
        timeout=timeout,
        max_concurrent=max_concurrent,
        skip_validation=skip_validation,
    )
    return ValidationClient(config=config)
