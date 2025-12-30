"""Shannon entropy calculation for secret detection.

This module provides functions for calculating the entropy of strings,
which helps distinguish high-randomness secrets from normal text.
"""

import math
from collections import Counter


def calculate_entropy(text: str) -> float:
    """Calculate Shannon entropy of a string.

    Higher entropy indicates more randomness (likely a secret).

    Typical thresholds:
    - < 3.0: Low entropy (common words, repeated chars)
    - 3.0-4.0: Medium entropy (mixed content)
    - 4.0-5.0: High entropy (potential secrets)
    - > 5.0: Very high entropy (likely cryptographic)

    Args:
        text: The string to analyze.

    Returns:
        Entropy value in bits per character.

    Examples:
        >>> calculate_entropy("aaaaaaa")  # Low entropy
        0.0
        >>> calculate_entropy("abc123XYZ")  # Higher entropy
        3.169...
    """
    if not text:
        return 0.0

    # Count character frequencies
    freq = Counter(text)
    length = len(text)

    # Calculate entropy: -Σ p(x) * log2(p(x))
    entropy = 0.0
    for count in freq.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy


def is_high_entropy(text: str, threshold: float = 4.5) -> bool:
    """Check if text has high entropy (likely a secret).

    Args:
        text: The string to check.
        threshold: Minimum entropy to be considered high.

    Returns:
        True if entropy exceeds threshold.

    Examples:
        >>> is_high_entropy("password123")
        False
        >>> is_high_entropy("a8f3k2m9x7n4p1q6")
        True
    """
    return calculate_entropy(text) >= threshold


def detect_charset(text: str) -> str:
    """Detect the character set of a string.

    Useful for identifying the type of encoding used in a potential secret.

    Args:
        text: The string to analyze.

    Returns:
        One of: 'empty', 'hex', 'base64', 'alphanumeric', 'mixed'

    Examples:
        >>> detect_charset("abc123")
        'alphanumeric'
        >>> detect_charset("deadbeef")
        'hex'
    """
    if not text:
        return "empty"

    hex_chars = set("0123456789abcdefABCDEF")
    base64_chars = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
    )
    alphanum_chars = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    )

    text_chars = set(text)

    if text_chars <= hex_chars:
        return "hex"
    elif text_chars <= alphanum_chars:
        return "alphanumeric"
    elif text_chars <= base64_chars:
        return "base64"
    else:
        return "mixed"


def calculate_entropy_ratio(text: str) -> float:
    """Calculate entropy as a ratio of maximum possible entropy.

    Maximum entropy for a string of length n using unique characters
    would be log2(n) for n unique characters.

    Args:
        text: The string to analyze.

    Returns:
        Ratio between 0.0 and 1.0, where 1.0 means maximum entropy.
    """
    if not text:
        return 0.0

    actual_entropy = calculate_entropy(text)
    max_entropy = math.log2(len(text)) if len(text) > 1 else 1.0

    return actual_entropy / max_entropy if max_entropy > 0 else 0.0
