"""Scan orchestrator that coordinates the full scanning workflow.

This module ties together all components:
- FileWalker for directory traversal
- GitFetcher for repository cloning
- PatternScanner for secret detection
- ValidationClient for key validation
- Reporters for output formatting
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from ai_truffle_hog.core.scanner import create_scanner
from ai_truffle_hog.fetcher.file_walker import create_default_walker
from ai_truffle_hog.fetcher.git import GitFetcher
from ai_truffle_hog.reporter.console import (
    ConsoleSummary,
    create_console_reporter,
)
from ai_truffle_hog.reporter.json_reporter import create_json_reporter
from ai_truffle_hog.reporter.sarif import create_sarif_reporter
from ai_truffle_hog.validator.client import (
    SecretCandidate,
    ValidationStats,
    create_validation_client,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ai_truffle_hog.core.scanner import ScanMatch

logger = logging.getLogger(__name__)


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    SARIF = "sarif"


@dataclass
class ScanResult:
    """Result of a scan operation.

    Attributes:
        target: What was scanned (URL, path).
        matches: List of detected secrets.
        total_files: Number of files scanned.
        validation_stats: Optional validation statistics.
        errors: List of errors encountered.
        success: Whether the scan completed successfully.
    """

    target: str
    matches: list[ScanMatch] = field(default_factory=list)
    total_files: int = 0
    validation_stats: ValidationStats | None = None
    errors: list[str] = field(default_factory=list)
    success: bool = True

    @property
    def total_matches(self) -> int:
        """Total number of matches found."""
        return len(self.matches)


@dataclass
class ScanConfig:
    """Configuration for scanning.

    Attributes:
        validate: Whether to validate discovered keys.
        output_format: Output format for results.
        providers: List of providers to scan for (None = all).
        scan_history: Whether to scan git history.
        verbose: Whether to show verbose output.
        output_file: Path to write output file.
    """

    validate: bool = False
    output_format: OutputFormat = OutputFormat.TABLE
    providers: list[str] | None = None
    scan_history: bool = False
    verbose: bool = False
    output_file: Path | None = None


class ScanOrchestrator:
    """Orchestrates the full scanning workflow.

    Coordinates:
    - Repository cloning (GitFetcher)
    - File discovery (FileWalker)
    - Secret scanning (PatternScanner)
    - Key validation (ValidationClient)
    - Result reporting (Reporters)

    Example:
        ```python
        orchestrator = ScanOrchestrator(ScanConfig(validate=True))
        result = await orchestrator.scan_repo("https://github.com/user/repo")
        orchestrator.print_results(result)
        ```
    """

    def __init__(self, config: ScanConfig | None = None) -> None:
        """Initialize the orchestrator.

        Args:
            config: Scan configuration.
        """
        self.config = config or ScanConfig()

        # Initialize components (walker created per-scan with specific root)
        self._scanner = create_scanner(providers=self.config.providers)
        self._console_reporter = create_console_reporter(verbose=self.config.verbose)
        self._json_reporter = create_json_reporter()
        self._sarif_reporter = create_sarif_reporter()

    def _matches_to_candidates(
        self,
        matches: list[ScanMatch],
    ) -> list[SecretCandidate]:
        """Convert ScanMatches to SecretCandidates for validation.

        Args:
            matches: List of scan matches.

        Returns:
            List of SecretCandidates.
        """
        return [
            SecretCandidate(
                provider_name=m.provider,
                secret_value=m.secret_value,
                file_path=m.file_path,
                line_number=m.line_number,
            )
            for m in matches
        ]

    async def _validate_matches(
        self,
        matches: list[ScanMatch],
    ) -> ValidationStats:
        """Validate discovered matches.

        Args:
            matches: List of matches to validate.

        Returns:
            Validation statistics.
        """
        candidates = self._matches_to_candidates(matches)

        async with create_validation_client() as client:
            _, stats = await client.validate_batch(candidates)

        return stats

    def _scan_directory(self, directory: Path) -> ScanResult:
        """Scan a local directory.

        Args:
            directory: Path to directory to scan.

        Returns:
            ScanResult with matches.
        """
        from pathlib import Path as PathClass

        result = ScanResult(target=str(directory))
        all_matches: list[ScanMatch] = []

        try:
            # Create walker for this specific directory
            walker = create_default_walker(directory)

            for file_info in walker.walk():
                result.total_files += 1

                matches = self._scanner.scan_file(PathClass(file_info.path))
                all_matches.extend(matches)

        except Exception as e:
            logger.exception("Error scanning directory")
            result.errors.append(str(e))
            result.success = False

        result.matches = all_matches
        return result

    async def scan_local(self, path: Path) -> ScanResult:
        """Scan a local path (file or directory).

        Args:
            path: Path to scan.

        Returns:
            ScanResult with findings.
        """
        if not path.exists():
            return ScanResult(
                target=str(path),
                success=False,
                errors=[f"Path does not exist: {path}"],
            )

        if path.is_file():
            result = ScanResult(target=str(path), total_files=1)
            result.matches = self._scanner.scan_file(path)
        else:
            result = self._scan_directory(path)

        # Validate if requested
        if self.config.validate and result.matches:
            result.validation_stats = await self._validate_matches(result.matches)

        return result

    async def scan_repo(self, url: str) -> ScanResult:
        """Scan a GitHub repository.

        Args:
            url: Repository URL to scan.

        Returns:
            ScanResult with findings.
        """
        result = ScanResult(target=url)

        try:
            with GitFetcher(url=url) as fetcher:
                fetcher.clone(depth=1)  # Shallow clone for speed
                repo_path = fetcher.repo_path

                if repo_path is None:
                    result.success = False
                    result.errors.append("Failed to clone repository")
                    return result

                # Scan the cloned directory
                local_result = await self.scan_local(repo_path)
                result.matches = local_result.matches
                result.total_files = local_result.total_files
                result.errors = local_result.errors
                result.validation_stats = local_result.validation_stats

        except Exception as e:
            logger.exception("Error scanning repository")
            result.success = False
            result.errors.append(str(e))

        return result

    async def scan_batch(self, targets: Sequence[str]) -> list[ScanResult]:
        """Scan multiple targets.

        Args:
            targets: List of URLs or paths to scan.

        Returns:
            List of ScanResults.
        """
        from pathlib import Path as PathClass

        results: list[ScanResult] = []

        for target in targets:
            if target.startswith(("http://", "https://", "git@")):
                result = await self.scan_repo(target)
            else:
                result = await self.scan_local(PathClass(target))
            results.append(result)

        return results

    def print_results(self, result: ScanResult) -> None:
        """Print results using the configured reporter.

        Args:
            result: Scan result to display.
        """
        if self.config.output_format == OutputFormat.TABLE:
            self._print_table_results(result)
        elif self.config.output_format == OutputFormat.JSON:
            self._print_json_results(result)
        elif self.config.output_format == OutputFormat.SARIF:
            self._print_sarif_results(result)

    def _print_table_results(self, result: ScanResult) -> None:
        """Print results as a Rich table."""
        self._console_reporter.print_header()
        self._console_reporter.print_matches(result.matches)

        # Build summary
        summary = ConsoleSummary(
            total_files=result.total_files,
            total_matches=result.total_matches,
        )
        for match in result.matches:
            summary.matches_by_provider[match.provider] = (
                summary.matches_by_provider.get(match.provider, 0) + 1
            )

        if result.validation_stats:
            summary.validated_count = result.validation_stats.validated
            summary.valid_count = result.validation_stats.valid

        self._console_reporter.print_summary(summary)

        # Print errors
        for error in result.errors:
            self._console_reporter.print_error(error)

    def _print_json_results(self, result: ScanResult) -> None:
        """Print results as JSON."""
        json_output = self._json_reporter.generate_json(
            result.matches,
            scan_target=result.target,
        )
        print(json_output)

    def _print_sarif_results(self, result: ScanResult) -> None:
        """Print results as SARIF."""
        sarif_output = self._sarif_reporter.generate_json(result.matches)
        print(sarif_output)

    def write_results(self, result: ScanResult, output_path: Path) -> None:
        """Write results to a file.

        Args:
            result: Scan result to write.
            output_path: Path to write to.
        """
        if self.config.output_format == OutputFormat.JSON:
            self._json_reporter.write(
                result.matches,
                output_path,
                scan_target=result.target,
            )
        elif self.config.output_format == OutputFormat.SARIF:
            self._sarif_reporter.write(result.matches, output_path)
        else:
            # For table, write JSON
            self._json_reporter.write(
                result.matches,
                output_path,
                scan_target=result.target,
            )


def create_orchestrator(
    validate: bool = False,
    output_format: str = "table",
    providers: list[str] | None = None,
    verbose: bool = False,
) -> ScanOrchestrator:
    """Create a configured scan orchestrator.

    Args:
        validate: Whether to validate discovered keys.
        output_format: Output format (table, json, sarif).
        providers: List of providers to scan for.
        verbose: Whether to show verbose output.

    Returns:
        Configured ScanOrchestrator.
    """
    config = ScanConfig(
        validate=validate,
        output_format=OutputFormat(output_format),
        providers=providers,
        verbose=verbose,
    )
    return ScanOrchestrator(config=config)
