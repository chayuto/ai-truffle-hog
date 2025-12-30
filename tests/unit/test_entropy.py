"""Unit tests for entropy calculation utilities."""

from ai_truffle_hog.utils.entropy import (
    calculate_entropy,
    calculate_entropy_ratio,
    detect_charset,
    is_high_entropy,
)


class TestCalculateEntropy:
    """Tests for calculate_entropy function."""

    def test_empty_string(self) -> None:
        """Empty string should have zero entropy."""
        assert calculate_entropy("") == 0.0

    def test_single_character_repeated(self) -> None:
        """Repeated single character has zero entropy."""
        assert calculate_entropy("aaaaaaa") == 0.0

    def test_two_characters_equal(self) -> None:
        """Two characters with equal frequency have entropy 1."""
        result = calculate_entropy("ab")
        assert abs(result - 1.0) < 0.001

    def test_high_entropy_random(self) -> None:
        """Random-looking string has high entropy."""
        # Using a mix of different character types
        random_like = "aB3xK9mZ2pQ7nR5"
        result = calculate_entropy(random_like)
        assert result > 3.5

    def test_low_entropy_word(self) -> None:
        """Common word has lower entropy."""
        result = calculate_entropy("password")
        # 'password' has only 6 unique chars in 8 total
        assert result < 3.0

    def test_api_key_like(self) -> None:
        """API key patterns should have high entropy."""
        api_key = "sk-proj-abc123def456ghi789jkl012mno345"
        result = calculate_entropy(api_key)
        assert result > 4.0


class TestIsHighEntropy:
    """Tests for is_high_entropy function."""

    def test_low_entropy_returns_false(self) -> None:
        """Low entropy string returns False."""
        assert is_high_entropy("password123") is False

    def test_high_entropy_returns_true(self) -> None:
        """High entropy string returns True."""
        # Long random-looking string
        assert is_high_entropy("aB3xK9mZ2pQ7nR5yU8wE1tS4iO6lH") is True

    def test_custom_threshold(self) -> None:
        """Custom threshold is respected."""
        medium = "abc123XYZ789"
        # With default high threshold
        assert is_high_entropy(medium, threshold=5.0) is False
        # With lower threshold
        assert is_high_entropy(medium, threshold=3.0) is True


class TestDetectCharset:
    """Tests for detect_charset function."""

    def test_empty(self) -> None:
        """Empty string returns 'empty'."""
        assert detect_charset("") == "empty"

    def test_hex(self) -> None:
        """Hex string is detected."""
        assert detect_charset("deadbeef") == "hex"
        assert detect_charset("0123456789ABCDEF") == "hex"

    def test_alphanumeric(self) -> None:
        """Alphanumeric string is detected."""
        assert detect_charset("abc123XYZ") == "alphanumeric"

    def test_base64(self) -> None:
        """Base64 string is detected."""
        assert detect_charset("abc123+/=") == "base64"

    def test_mixed(self) -> None:
        """Mixed charset with special chars is detected."""
        assert detect_charset("abc!@#$%") == "mixed"


class TestCalculateEntropyRatio:
    """Tests for calculate_entropy_ratio function."""

    def test_empty_string(self) -> None:
        """Empty string returns 0."""
        assert calculate_entropy_ratio("") == 0.0

    def test_returns_ratio_between_0_and_1(self) -> None:
        """Result should be normalized between 0 and 1."""
        result = calculate_entropy_ratio("aB3xK9mZ2pQ7nR5")
        assert 0.0 <= result <= 1.0

    def test_repeated_chars_low_ratio(self) -> None:
        """Repeated characters have low ratio."""
        result = calculate_entropy_ratio("aaaaaaa")
        assert result == 0.0
