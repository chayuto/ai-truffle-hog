"""Pattern scanning engine.

This module provides the core scanning functionality that detects
secrets using regex patterns from registered providers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ai_truffle_hog.providers.registry import get_registry
from ai_truffle_hog.utils.entropy import calculate_entropy

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from ai_truffle_hog.providers.base import BaseProvider


@dataclass
class ScanMatch:
    """Individual secret match result.

    Represents a single detected secret with its location,
    context, and metadata.

    Attributes:
        provider: Name of the provider that matched.
        pattern_name: Description of the pattern that matched.
        secret_value: The matched secret value.
        line_number: Line number where secret was found (1-indexed).
        column_start: Starting column position (0-indexed).
        column_end: Ending column position (0-indexed).
        line_content: The full line containing the secret.
        context_before: Lines before the match (for context).
        context_after: Lines after the match (for context).
        entropy: Shannon entropy of the secret.
        file_path: Path to the file (if scanning a file).
        variable_name: Detected variable name (if any).
    """

    provider: str
    pattern_name: str
    secret_value: str
    line_number: int
    column_start: int
    column_end: int
    line_content: str
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    entropy: float = 0.0
    file_path: str = ""
    variable_name: str | None = None

    @property
    def redacted_value(self) -> str:
        """Return a redacted version of the secret."""
        if len(self.secret_value) <= 8:
            return "*" * len(self.secret_value)
        return (
            self.secret_value[:4]
            + "*" * (len(self.secret_value) - 8)
            + self.secret_value[-4:]
        )


# Common variable name patterns for context extraction
VARIABLE_PATTERN = re.compile(
    r"""
    (?:
        # Python/JS/Go assignment: var_name = "value"
        ([a-zA-Z_][a-zA-Z0-9_]*)\s*[:=]\s*["']
        |
        # JSON/YAML: "key": "value" or key: value
        ["']?([a-zA-Z_][a-zA-Z0-9_]*)["']?\s*[:=]\s*["']?
        |
        # Environment variable: EXPORT VAR=value
        \b([A-Z_][A-Z0-9_]*)\s*=
    )
    """,
    re.VERBOSE,
)


class PatternScanner:
    """Core scanning engine for detecting secrets.

    Applies regex patterns from registered providers to content
    and returns detailed match information.

    Example:
        >>> scanner = PatternScanner()
        >>> matches = scanner.scan_content('api_key = "sk-abc123..."')
        >>> for match in matches:
        ...     print(f"{match.provider}: {match.redacted_value}")
    """

    def __init__(
        self,
        providers: list[str] | None = None,
        context_lines: int = 3,
    ) -> None:
        """Initialize the scanner.

        Args:
            providers: List of provider names to use. If None, uses all.
            context_lines: Number of context lines before/after match.
        """
        self.context_lines = context_lines
        self._registry = get_registry()

        # Filter providers if specified
        if providers:
            self._providers = [p for p in self._registry.all() if p.name in providers]
        else:
            self._providers = list(self._registry.all())

    @property
    def provider_count(self) -> int:
        """Number of providers being used."""
        return len(self._providers)

    @property
    def pattern_count(self) -> int:
        """Total number of patterns across all providers."""
        return sum(len(p.patterns) for p in self._providers)

    @property
    def provider_names(self) -> list[str]:
        """Names of all providers being used."""
        return [p.name for p in self._providers]

    def scan_content(
        self,
        content: str,
        file_path: str = "<string>",
    ) -> list[ScanMatch]:
        """Scan content for secrets using all provider patterns.

        Args:
            content: Text content to scan.
            file_path: Optional file path for context.

        Returns:
            List of ScanMatch objects for each detected secret.
        """
        if not content:
            return []

        lines = content.splitlines()
        matches: list[ScanMatch] = []
        seen_secrets: set[tuple[str, int, int]] = set()  # Dedupe

        for provider in self._providers:
            for pattern_idx, pattern in enumerate(provider.patterns):
                pattern_name = f"{provider.display_name} Pattern {pattern_idx + 1}"
                provider_matches = self._find_matches(
                    content=content,
                    lines=lines,
                    provider=provider,
                    pattern=pattern,
                    pattern_name=pattern_name,
                    file_path=file_path,
                    seen_secrets=seen_secrets,
                )
                matches.extend(provider_matches)

        return matches

    def _find_matches(
        self,
        content: str,
        lines: list[str],
        provider: BaseProvider,
        pattern: re.Pattern[str],
        pattern_name: str,
        file_path: str,
        seen_secrets: set[tuple[str, int, int]],
    ) -> list[ScanMatch]:
        """Find matches for a single pattern.

        Args:
            content: Full content being scanned.
            lines: Content split into lines.
            provider: Provider instance.
            pattern: Compiled regex pattern.
            pattern_name: Name for this pattern.
            file_path: File path for context.
            seen_secrets: Set of already-seen secrets for deduplication.

        Returns:
            List of matches found.
        """
        matches: list[ScanMatch] = []

        for match in pattern.finditer(content):
            # Get the matched secret (use group 1 if exists, else group 0)
            secret_value = match.group(1) if match.lastindex else match.group(0)

            # Find line number and column
            start_pos = match.start(1) if match.lastindex else match.start(0)
            line_number, column_start = self._position_to_line_col(content, start_pos)
            column_end = column_start + len(secret_value)

            # Deduplicate by (secret, line, column)
            dedup_key = (secret_value, line_number, column_start)
            if dedup_key in seen_secrets:
                continue
            seen_secrets.add(dedup_key)

            # Get line content and context
            line_content = lines[line_number - 1] if line_number <= len(lines) else ""
            context_before = self._get_context_before(lines, line_number)
            context_after = self._get_context_after(lines, line_number)

            # Extract variable name if detectable
            variable_name = self._extract_variable_name(line_content, column_start)

            # Calculate entropy
            entropy = calculate_entropy(secret_value)

            matches.append(
                ScanMatch(
                    provider=provider.name,
                    pattern_name=pattern_name,
                    secret_value=secret_value,
                    line_number=line_number,
                    column_start=column_start,
                    column_end=column_end,
                    line_content=line_content,
                    context_before=context_before,
                    context_after=context_after,
                    entropy=entropy,
                    file_path=file_path,
                    variable_name=variable_name,
                )
            )

        return matches

    def _position_to_line_col(self, content: str, pos: int) -> tuple[int, int]:
        """Convert character position to line number and column.

        Args:
            content: The content string.
            pos: Character position.

        Returns:
            Tuple of (line_number, column), 1-indexed for line.
        """
        lines_before = content[:pos].split("\n")
        line_number = len(lines_before)
        column = len(lines_before[-1])
        return line_number, column

    def _get_context_before(self, lines: list[str], line_number: int) -> list[str]:
        """Get lines before the match for context."""
        start_idx = max(0, line_number - 1 - self.context_lines)
        end_idx = line_number - 1
        return lines[start_idx:end_idx]

    def _get_context_after(self, lines: list[str], line_number: int) -> list[str]:
        """Get lines after the match for context."""
        start_idx = line_number
        end_idx = min(len(lines), line_number + self.context_lines)
        return lines[start_idx:end_idx]

    def _extract_variable_name(
        self,
        line_content: str,
        column: int,
    ) -> str | None:
        """Try to extract variable name from the line.

        Args:
            line_content: The line containing the secret.
            column: Column position of the secret.

        Returns:
            Variable name if detected, None otherwise.
        """
        # Look at the part of the line before the secret
        prefix = line_content[:column]

        # Try to match variable assignment patterns
        for match in VARIABLE_PATTERN.finditer(prefix):
            # Get the last match (closest to the secret)
            var_name = match.group(1) or match.group(2) or match.group(3)
            if var_name:
                return var_name

        return None

    def scan_file(self, file_path: Path) -> list[ScanMatch]:
        """Scan a file for secrets.

        Args:
            file_path: Path to the file to scan.

        Returns:
            List of ScanMatch objects found in the file.

        Raises:
            OSError: If file cannot be read.
        """
        # Try UTF-8 first, fall back to latin-1
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1")

        return self.scan_content(content, str(file_path))

    def scan_file_safe(
        self,
        file_path: Path,
    ) -> tuple[list[ScanMatch], str | None]:
        """Scan a file safely, returning error info if failed.

        Args:
            file_path: Path to the file to scan.

        Returns:
            Tuple of (matches, error_message).
            If successful, error_message is None.
        """
        try:
            matches = self.scan_file(file_path)
            return matches, None
        except OSError as e:
            return [], f"IO error: {e}"
        except Exception as e:
            return [], f"Error scanning file: {e}"

    def iter_scan_files(
        self,
        file_paths: list[Path],
    ) -> Iterator[tuple[Path, list[ScanMatch], str | None]]:
        """Iterate over files, scanning each one.

        Args:
            file_paths: List of file paths to scan.

        Yields:
            Tuple of (file_path, matches, error_message).
        """
        for file_path in file_paths:
            matches, error = self.scan_file_safe(file_path)
            yield file_path, matches, error


def create_scanner(
    providers: list[str] | None = None,
    context_lines: int = 3,
) -> PatternScanner:
    """Create a PatternScanner with configuration.

    Args:
        providers: List of provider names to use.
        context_lines: Number of context lines.

    Returns:
        Configured PatternScanner instance.
    """
    return PatternScanner(providers=providers, context_lines=context_lines)
