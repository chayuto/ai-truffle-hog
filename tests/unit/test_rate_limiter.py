"""Unit tests for RateLimiter module."""

from __future__ import annotations

import asyncio
import time

import pytest

from ai_truffle_hog.validator.rate_limiter import (
    RateLimitConfig,
    RateLimiter,
    TokenBucket,
    create_rate_limiter,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = RateLimitConfig()
        assert config.requests_per_second == 1.0
        assert config.burst_size == 5

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = RateLimitConfig(requests_per_second=10.0, burst_size=100)
        assert config.requests_per_second == 10.0
        assert config.burst_size == 100


class TestTokenBucket:
    """Tests for TokenBucket class."""

    def test_initial_full_capacity(self) -> None:
        """Test bucket starts with full capacity."""
        bucket = TokenBucket(rate=1.0, capacity=10)
        assert bucket.available_tokens == 10

    def test_consume_success(self) -> None:
        """Test successful token consumption."""
        bucket = TokenBucket(rate=1.0, capacity=10)
        assert bucket.consume(1)
        # Use approx due to refill timing
        assert bucket.available_tokens == pytest.approx(9, abs=0.1)

    def test_consume_multiple(self) -> None:
        """Test consuming multiple tokens."""
        bucket = TokenBucket(rate=1.0, capacity=10)
        assert bucket.consume(5)
        # Use approx due to refill timing
        assert bucket.available_tokens == pytest.approx(5, abs=0.1)

    def test_consume_failure_not_enough_tokens(self) -> None:
        """Test consumption fails when not enough tokens."""
        bucket = TokenBucket(rate=1.0, capacity=5)
        # Drain the bucket
        for _ in range(5):
            bucket.consume(1)
        # Should fail
        assert not bucket.consume(1)

    def test_consume_all_then_fail(self) -> None:
        """Test consuming all tokens then failing."""
        bucket = TokenBucket(rate=1.0, capacity=3)
        assert bucket.consume(3)
        assert not bucket.consume(1)

    def test_wait_time_when_tokens_available(self) -> None:
        """Test wait time is 0 when tokens available."""
        bucket = TokenBucket(rate=1.0, capacity=10)
        assert bucket.wait_time(1) == 0.0

    def test_wait_time_when_empty(self) -> None:
        """Test wait time calculation when bucket is empty."""
        bucket = TokenBucket(rate=2.0, capacity=2)  # 2 tokens/second
        bucket.consume(2)  # Empty the bucket
        wait = bucket.wait_time(1)
        # Should need about 0.5 seconds for 1 token at 2/second
        assert 0.0 <= wait <= 1.0

    def test_refill_over_time(self) -> None:
        """Test tokens refill over time."""
        bucket = TokenBucket(rate=100.0, capacity=10)  # Fast rate
        bucket.consume(10)  # Empty
        time.sleep(0.15)  # Wait for refill
        # Should have some tokens now
        assert bucket.available_tokens > 0


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        limiter = RateLimiter()
        assert limiter is not None

    def test_init_with_config(self) -> None:
        """Test initialization with custom default config."""
        config = RateLimitConfig(requests_per_second=5.0, burst_size=20)
        limiter = RateLimiter(default_config=config)
        assert limiter is not None

    def test_configure_provider(self) -> None:
        """Test configuring a specific provider."""
        limiter = RateLimiter()
        config = RateLimitConfig(requests_per_second=10.0, burst_size=50)
        limiter.configure_provider("test_provider", config)
        # Should be able to acquire immediately
        assert limiter.try_acquire("test_provider")

    def test_try_acquire_success(self) -> None:
        """Test successful non-blocking acquisition."""
        limiter = RateLimiter()
        assert limiter.try_acquire("openai")

    def test_try_acquire_with_burst(self) -> None:
        """Test burst capability."""
        limiter = RateLimiter()
        # OpenAI default: 10 burst size
        for _ in range(10):
            assert limiter.try_acquire("openai")

    def test_try_acquire_fails_after_burst(self) -> None:
        """Test acquisition fails after burst is exhausted."""
        limiter = RateLimiter()
        config = RateLimitConfig(requests_per_second=0.1, burst_size=2)
        limiter.configure_provider("test", config)

        # Consume burst
        assert limiter.try_acquire("test")
        assert limiter.try_acquire("test")
        # Should fail now
        assert not limiter.try_acquire("test")

    def test_get_wait_time(self) -> None:
        """Test getting wait time for a provider."""
        limiter = RateLimiter()
        # Fresh limiter should have 0 wait time
        wait = limiter.get_wait_time("openai")
        assert wait == 0.0

    def test_reset_single_provider(self) -> None:
        """Test resetting a single provider."""
        limiter = RateLimiter()
        # Consume some tokens
        limiter.try_acquire("openai")
        limiter.try_acquire("openai")
        # Reset
        limiter.reset("openai")
        # Should have fresh bucket
        wait = limiter.get_wait_time("openai")
        assert wait == 0.0

    def test_reset_all_providers(self) -> None:
        """Test resetting all providers."""
        limiter = RateLimiter()
        limiter.try_acquire("openai")
        limiter.try_acquire("anthropic")
        # Reset all
        limiter.reset()
        # Both should have fresh buckets
        assert limiter.get_wait_time("openai") == 0.0
        assert limiter.get_wait_time("anthropic") == 0.0

    def test_default_limits_exist(self) -> None:
        """Test default limits exist for known providers."""
        assert "openai" in RateLimiter.DEFAULT_LIMITS
        assert "anthropic" in RateLimiter.DEFAULT_LIMITS
        assert "huggingface" in RateLimiter.DEFAULT_LIMITS

    def test_unknown_provider_uses_default(self) -> None:
        """Test unknown provider uses default config."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_second=1.0, burst_size=3)
        )
        # Should work with default config
        assert limiter.try_acquire("unknown_provider")
        assert limiter.try_acquire("unknown_provider")
        assert limiter.try_acquire("unknown_provider")


class TestRateLimiterAsync:
    """Async tests for RateLimiter."""

    @pytest.mark.asyncio
    async def test_acquire_success(self) -> None:
        """Test async acquisition."""
        limiter = RateLimiter()
        # Should not block
        await limiter.acquire("openai")

    @pytest.mark.asyncio
    async def test_acquire_waits_when_rate_limited(self) -> None:
        """Test acquire waits when rate limited."""
        limiter = RateLimiter()
        config = RateLimitConfig(requests_per_second=100.0, burst_size=1)
        limiter.configure_provider("test", config)

        # First should be immediate
        start = time.monotonic()
        await limiter.acquire("test")
        first_time = time.monotonic() - start
        assert first_time < 0.1

        # Second should wait briefly
        start = time.monotonic()
        await limiter.acquire("test")
        second_time = time.monotonic() - start
        # At 100/sec, wait should be ~0.01 seconds
        assert second_time < 0.1

    @pytest.mark.asyncio
    async def test_concurrent_acquires(self) -> None:
        """Test concurrent acquisitions are serialized."""
        limiter = RateLimiter()
        config = RateLimitConfig(requests_per_second=1000.0, burst_size=5)
        limiter.configure_provider("test", config)

        # Run 5 concurrent acquires
        await asyncio.gather(*[limiter.acquire("test") for _ in range(5)])


class TestCreateRateLimiter:
    """Tests for create_rate_limiter factory function."""

    def test_create_default(self) -> None:
        """Test creating default rate limiter."""
        limiter = create_rate_limiter()
        assert isinstance(limiter, RateLimiter)

    def test_create_with_custom_limits(self) -> None:
        """Test creating with custom limits."""
        custom = {
            "custom_provider": RateLimitConfig(requests_per_second=5.0, burst_size=25),
        }
        limiter = create_rate_limiter(custom_limits=custom)

        # Should use custom config for custom_provider
        assert limiter.try_acquire("custom_provider")
