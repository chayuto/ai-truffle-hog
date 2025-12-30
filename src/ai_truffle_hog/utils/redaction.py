"""Secret redaction utilities for safe logging.

This module provides functions for redacting sensitive values
before they are written to logs or displayed to users.
"""

from collections.abc import Callable


def redact_secret(
    secret: str,
    show_prefix: int = 8,
    show_suffix: int = 4,
    mask_char: str = "*",
    min_length_to_redact: int = 12,
) -> str:
    """Redact a secret for safe display.

    Shows a portion of the beginning and end of the secret while
    masking the middle section.

    Args:
        secret: The secret value to redact.
        show_prefix: Number of characters to show at the start.
        show_suffix: Number of characters to show at the end.
        mask_char: Character to use for masking.
        min_length_to_redact: Secrets shorter than this are fully masked.

    Returns:
        Redacted string like "sk-proj-****...****xyz9"

    Examples:
        >>> redact_secret("sk-proj-abc123xyz")
        'sk-proj-****...****xyz'
        >>> redact_secret("short")
        '*****'
    """
    if not secret:
        return ""

    length = len(secret)

    # Fully mask short secrets
    if length < min_length_to_redact:
        return mask_char * length

    # Adjust if secret is too short for prefix+suffix
    if show_prefix + show_suffix >= length:
        show_prefix = length // 3
        show_suffix = length // 3

    prefix = secret[:show_prefix]
    suffix = secret[-show_suffix:] if show_suffix > 0 else ""

    return f"{prefix}{mask_char * 4}...{mask_char * 4}{suffix}"


def redact_in_text(
    text: str,
    secret: str,
    replacement: str | None = None,
) -> str:
    """Replace occurrences of a secret in text with redacted version.

    Args:
        text: Text that may contain the secret.
        secret: The secret value to redact.
        replacement: Custom replacement string (default: auto-redact).

    Returns:
        Text with all occurrences of the secret redacted.

    Examples:
        >>> redact_in_text("key=sk-abc123xyz", "sk-abc123xyz")
        'key=sk-abc12****...****3xyz'
    """
    if not secret or not text:
        return text

    if replacement is None:
        replacement = redact_secret(secret)

    return text.replace(secret, replacement)


def create_redaction_filter(secrets: list[str]) -> Callable[[str], str]:
    """Create a filter function that redacts multiple secrets.

    Args:
        secrets: List of secret values to redact.

    Returns:
        A function that takes text and returns redacted text.
    """

    def filter_func(text: str) -> str:
        result = text
        for secret in secrets:
            result = redact_in_text(result, secret)
        return result

    return filter_func
