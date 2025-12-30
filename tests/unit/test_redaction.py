"""Unit tests for redaction utilities."""

from ai_truffle_hog.utils.redaction import (
    create_redaction_filter,
    redact_in_text,
    redact_secret,
)


class TestRedactSecret:
    """Tests for redact_secret function."""

    def test_empty_string(self) -> None:
        """Empty string returns empty."""
        assert redact_secret("") == ""

    def test_short_secret_fully_masked(self) -> None:
        """Short secrets are fully masked."""
        result = redact_secret("short")
        assert "*" in result
        assert "short" not in result

    def test_long_secret_partial_redaction(self) -> None:
        """Long secrets show prefix and suffix."""
        secret = "sk-proj-abc123def456ghi789jkl"
        result = redact_secret(secret)

        # Should show beginning
        assert result.startswith("sk-proj-")
        # Should contain mask
        assert "****" in result
        # Should not contain full secret
        assert secret not in result

    def test_custom_mask_char(self) -> None:
        """Custom mask character is used."""
        result = redact_secret("longersecretvalue", mask_char="#")
        assert "####" in result

    def test_preserves_prefix_length(self) -> None:
        """Prefix length is preserved."""
        secret = "sk-proj-abc123xyz789"
        result = redact_secret(secret, show_prefix=8)
        assert result.startswith("sk-proj-")


class TestRedactInText:
    """Tests for redact_in_text function."""

    def test_empty_inputs(self) -> None:
        """Empty inputs return original."""
        assert redact_in_text("", "secret") == ""
        assert redact_in_text("text", "") == "text"

    def test_single_occurrence(self) -> None:
        """Single occurrence is redacted."""
        text = 'API_KEY = "sk-secret123456789"'
        secret = "sk-secret123456789"
        result = redact_in_text(text, secret)

        assert secret not in result
        assert "API_KEY" in result

    def test_multiple_occurrences(self) -> None:
        """Multiple occurrences are all redacted."""
        secret = "myapikey12345678"
        text = f"first: {secret}, second: {secret}"
        result = redact_in_text(text, secret)

        assert secret not in result
        assert "first:" in result
        assert "second:" in result

    def test_custom_replacement(self) -> None:
        """Custom replacement is used."""
        text = "key=secret123"
        result = redact_in_text(text, "secret123", replacement="[REDACTED]")
        assert result == "key=[REDACTED]"


class TestCreateRedactionFilter:
    """Tests for create_redaction_filter function."""

    def test_filters_multiple_secrets(self) -> None:
        """Filter removes multiple secrets."""
        secrets = ["secret1fortest", "secret2fortest"]
        filter_func = create_redaction_filter(secrets)

        text = "a: secret1fortest, b: secret2fortest"
        result = filter_func(text)

        assert "secret1fortest" not in result
        assert "secret2fortest" not in result

    def test_empty_secrets_list(self) -> None:
        """Empty secrets list returns original."""
        filter_func = create_redaction_filter([])
        text = "no secrets here"
        assert filter_func(text) == text
