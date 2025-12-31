"""Rate limiting for validation requests.

This module provides rate limiting functionality to prevent
overwhelming provider APIs during validation.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting a provider.

    Attributes:
        requests_per_second: Maximum requests per second.
        burst_size: Maximum burst of requests before rate limiting kicks in.
    """

    requests_per_second: float = 1.0
    burst_size: int = 5


@dataclass
class TokenBucket:
    """Token bucket implementation for rate limiting.

    Uses the token bucket algorithm for smooth rate limiting
    with burst capability.

    Attributes:
        rate: Tokens added per second.
        capacity: Maximum tokens in the bucket.
        tokens: Current number of tokens.
        last_update: Last time tokens were added.
    """

    rate: float
    capacity: int
    tokens: float = field(init=False)
    last_update: float = field(init=False)

    def __post_init__(self) -> None:
        """Initialize bucket with full capacity."""
        self.tokens = float(self.capacity)
        self.last_update = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            True if tokens were consumed, False if not enough tokens.
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def wait_time(self, tokens: int = 1) -> float:
        """Calculate time to wait before tokens are available.

        Args:
            tokens: Number of tokens needed.

        Returns:
            Time in seconds to wait (0 if tokens are available).
        """
        self._refill()
        if self.tokens >= tokens:
            return 0.0
        needed = tokens - self.tokens
        return needed / self.rate

    @property
    def available_tokens(self) -> float:
        """Get current number of available tokens."""
        self._refill()
        return self.tokens


class RateLimiter:
    """Rate limiter for API validation requests.

    Provides per-provider rate limiting using token buckets.
    Thread-safe for use in async contexts.

    Example:
        ```python
        limiter = RateLimiter()
        limiter.configure_provider("openai", RateLimitConfig(
            requests_per_second=2.0,
            burst_size=10
        ))

        async with limiter.acquire("openai"):
            # Make API request
            ...
        ```
    """

    # Default rate limits for known providers
    DEFAULT_LIMITS: ClassVar[dict[str, RateLimitConfig]] = {
        "openai": RateLimitConfig(requests_per_second=2.0, burst_size=10),
        "anthropic": RateLimitConfig(requests_per_second=2.0, burst_size=10),
        "huggingface": RateLimitConfig(requests_per_second=5.0, burst_size=20),
        "cohere": RateLimitConfig(requests_per_second=2.0, burst_size=10),
        "replicate": RateLimitConfig(requests_per_second=2.0, burst_size=10),
        "google_gemini": RateLimitConfig(requests_per_second=2.0, burst_size=10),
        "groq": RateLimitConfig(requests_per_second=5.0, burst_size=20),
        "langsmith": RateLimitConfig(requests_per_second=2.0, burst_size=10),
    }

    def __init__(
        self,
        default_config: RateLimitConfig | None = None,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            default_config: Default config for unknown providers.
        """
        self._default_config = default_config or RateLimitConfig(
            requests_per_second=1.0,
            burst_size=5,
        )
        self._buckets: defaultdict[str, TokenBucket] = defaultdict(
            self._create_default_bucket
        )
        self._configs: dict[str, RateLimitConfig] = {}
        self._lock = asyncio.Lock()

    def _create_default_bucket(self) -> TokenBucket:
        """Create a bucket with default configuration."""
        return TokenBucket(
            rate=self._default_config.requests_per_second,
            capacity=self._default_config.burst_size,
        )

    def configure_provider(
        self,
        provider_name: str,
        config: RateLimitConfig,
    ) -> None:
        """Configure rate limiting for a specific provider.

        Args:
            provider_name: Name of the provider.
            config: Rate limit configuration.
        """
        self._configs[provider_name] = config
        # Reset bucket with new config
        self._buckets[provider_name] = TokenBucket(
            rate=config.requests_per_second,
            capacity=config.burst_size,
        )

    def _get_bucket(self, provider_name: str) -> TokenBucket:
        """Get or create token bucket for a provider.

        Args:
            provider_name: Name of the provider.

        Returns:
            Token bucket for the provider.
        """
        if provider_name not in self._buckets:
            # Check for default limits
            config = self._configs.get(
                provider_name,
                self.DEFAULT_LIMITS.get(provider_name, self._default_config),
            )
            self._buckets[provider_name] = TokenBucket(
                rate=config.requests_per_second,
                capacity=config.burst_size,
            )
        return self._buckets[provider_name]

    async def acquire(self, provider_name: str) -> None:
        """Wait until rate limit allows a request.

        Args:
            provider_name: Name of the provider.
        """
        async with self._lock:
            bucket = self._get_bucket(provider_name)
            wait_time = bucket.wait_time()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            bucket.consume()

    def try_acquire(self, provider_name: str) -> bool:
        """Try to acquire rate limit without blocking.

        Args:
            provider_name: Name of the provider.

        Returns:
            True if acquired, False if rate limited.
        """
        bucket = self._get_bucket(provider_name)
        return bucket.consume()

    def get_wait_time(self, provider_name: str) -> float:
        """Get wait time until next request is allowed.

        Args:
            provider_name: Name of the provider.

        Returns:
            Time in seconds to wait (0 if can request now).
        """
        bucket = self._get_bucket(provider_name)
        return bucket.wait_time()

    def reset(self, provider_name: str | None = None) -> None:
        """Reset rate limiter state.

        Args:
            provider_name: Provider to reset, or None to reset all.
        """
        if provider_name:
            if provider_name in self._buckets:
                config = self._configs.get(
                    provider_name,
                    self.DEFAULT_LIMITS.get(provider_name, self._default_config),
                )
                self._buckets[provider_name] = TokenBucket(
                    rate=config.requests_per_second,
                    capacity=config.burst_size,
                )
        else:
            self._buckets.clear()


def create_rate_limiter(
    custom_limits: dict[str, RateLimitConfig] | None = None,
) -> RateLimiter:
    """Create a configured rate limiter.

    Args:
        custom_limits: Custom rate limits for specific providers.

    Returns:
        Configured RateLimiter instance.
    """
    limiter = RateLimiter()
    if custom_limits:
        for provider_name, config in custom_limits.items():
            limiter.configure_provider(provider_name, config)
    return limiter
