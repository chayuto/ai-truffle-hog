"""Scan orchestrator that coordinates the full scanning workflow.

This module ties together all components:
- FileWalker for directory traversal
- GitFetcher for repository cloning
- GitHistoryScanner for git history analysis
- PatternScanner for secret detection
- ValidationClient for key validation
- Reporters for output formatting
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from ai_truffle_hog.core.scanner import create_scanner
from ai_truffle_hog.fetcher.file_walker import create_default_walker
from ai_truffle_hog.fetcher.git import GitFetcher, GitHistoryScanner
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
    from ai_truffle_hog.fetcher.git import CommitInfo

logger = logging.getLogger(__name__)


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    SARIF = "sarif"


@dataclass
class HistoryMatch:
    """A secret found in git history.

    Attributes:
        match: The scan match with secret details.
        commit: The commit where it was found.
        is_deleted: Whether the secret has been deleted in later commits.
    """

    match: ScanMatch
    commit: CommitInfo
    is_deleted: bool = False


@dataclass
class ScanLog:
    """Detailed log of scan operations.

    Attributes:
        files_scanned: List of files that were scanned.
        commits_scanned: Number of commits scanned in history.
        branches_scanned: List of branches scanned.
        scan_start: When the scan started.
        scan_end: When the scan ended.
    """

    files_scanned: list[str] = field(default_factory=list)
    commits_scanned: int = 0
    branches_scanned: list[str] = field(default_factory=list)
    scan_start: datetime | None = None
    scan_end: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        """Get scan duration in seconds."""
        if self.scan_start and self.scan_end:
            return (self.scan_end - self.scan_start).total_seconds()
        return 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "files_scanned": self.files_scanned,
            "files_count": len(self.files_scanned),
            "commits_scanned": self.commits_scanned,
            "branches_scanned": self.branches_scanned,
            "scan_start": self.scan_start.isoformat() if self.scan_start else None,
            "scan_end": self.scan_end.isoformat() if self.scan_end else None,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class ScanResult:
    """Result of a scan operation.

    Attributes:
        target: What was scanned (URL, path).
        matches: List of detected secrets in current files.
        history_matches: List of secrets found in git history.
        total_files: Number of files scanned.
        validation_stats: Optional validation statistics.
        errors: List of errors encountered.
        success: Whether the scan completed successfully.
        scan_log: Detailed scan log with files scanned.
    """

    target: str
    matches: list[ScanMatch] = field(default_factory=list)
    history_matches: list[HistoryMatch] = field(default_factory=list)
    total_files: int = 0
    validation_stats: ValidationStats | None = None
    errors: list[str] = field(default_factory=list)
    success: bool = True
    scan_log: ScanLog = field(default_factory=ScanLog)

    @property
    def total_matches(self) -> int:
        """Total number of matches found (current + history)."""
        return len(self.matches) + len(self.history_matches)

    @property
    def current_matches_count(self) -> int:
        """Number of matches in current files."""
        return len(self.matches)

    @property
    def history_matches_count(self) -> int:
        """Number of matches in git history."""
        return len(self.history_matches)


@dataclass
class ScanConfig:
    """Configuration for scanning.

    Attributes:
        validate: Whether to validate discovered keys.
        output_format: Output format for results.
        providers: List of providers to scan for (None = all).
        scan_history: Whether to scan git history (ALL branches).
        scan_all_branches: Whether to scan all branches (default True).
        verbose: Whether to show verbose output.
        output_file: Path to write output file.
    """

    validate: bool = False
    output_format: OutputFormat = OutputFormat.TABLE
    providers: list[str] | None = None
    scan_history: bool = False
    scan_all_branches: bool = True
    verbose: bool = False
    output_file: Path | None = None


class ScanOrchestrator:
    """Orchestrates the full scanning workflow.

    Coordinates:
    - Repository cloning (GitFetcher)
    - Git history scanning (GitHistoryScanner) across ALL branches
    - File discovery (FileWalker)
    - Secret scanning (PatternScanner)
    - Key validation (ValidationClient)
    - Result reporting (Reporters)

    Example:
        ```python
        orchestrator = ScanOrchestrator(ScanConfig(validate=True, scan_history=True))
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

    def _scan_directory(
        self, directory: Path, scan_log: ScanLog | None = None
    ) -> ScanResult:
        """Scan a local directory.

        Args:
            directory: Path to directory to scan.
            scan_log: Optional scan log to populate with files scanned.

        Returns:
            ScanResult with matches.
        """
        from pathlib import Path as PathClass

        result = ScanResult(target=str(directory))
        if scan_log:
            result.scan_log = scan_log
        all_matches: list[ScanMatch] = []

        try:
            # Create walker for this specific directory
            walker = create_default_walker(directory)

            for file_info in walker.walk():
                result.total_files += 1
                # Log the file path (relative to directory for readability)
                try:
                    rel_path = PathClass(file_info.path).relative_to(directory)
                    result.scan_log.files_scanned.append(str(rel_path))
                except ValueError:
                    result.scan_log.files_scanned.append(file_info.path)

                matches = self._scanner.scan_file(PathClass(file_info.path))
                all_matches.extend(matches)

        except Exception as e:
            logger.exception("Error scanning directory")
            result.errors.append(str(e))
            result.success = False

        result.matches = all_matches
        return result

    def _scan_git_history(
        self,
        repo_path: Path,
        scan_log: ScanLog,
    ) -> list[HistoryMatch]:
        """Scan git history for secrets across ALL branches.

        Args:
            repo_path: Path to the git repository.
            scan_log: Scan log to update with commit/branch info.

        Returns:
            List of HistoryMatch objects.
        """
        from git import Repo

        history_matches: list[HistoryMatch] = []

        try:
            # Get all branches
            repo = Repo(repo_path)
            branches = [
                ref.name for ref in repo.refs if not ref.name.startswith("origin/HEAD")
            ]
            scan_log.branches_scanned = branches

            if self.config.verbose:
                logger.info(f"Scanning {len(branches)} branches for git history")

            # Use PyDriller to scan all commits across all branches
            # Setting only_in_branch=None scans all branches
            history_scanner = GitHistoryScanner(repo_path)

            seen_commits: set[str] = set()

            for commit_info, changes in history_scanner.iter_commits_with_changes():
                # Skip already processed commits (can appear in multiple branches)
                if commit_info.hash in seen_commits:
                    continue
                seen_commits.add(commit_info.hash)
                scan_log.commits_scanned += 1

                # Scan each file change in this commit
                for change in changes:
                    if change.content and not change.is_deleted:
                        # Scan the file content
                        matches = self._scanner.scan_content(
                            change.content,
                            file_path=change.path,
                        )
                        for match in matches:
                            history_matches.append(
                                HistoryMatch(
                                    match=match,
                                    commit=commit_info,
                                    is_deleted=False,
                                )
                            )

        except Exception:
            logger.exception("Error scanning git history")
            # Don't fail the whole scan, just log the error

        return history_matches

    async def scan_local(self, path: Path) -> ScanResult:
        """Scan a local path (file or directory).

        Args:
            path: Path to scan.

        Returns:
            ScanResult with findings.
        """
        scan_log = ScanLog(scan_start=datetime.now(UTC))

        if not path.exists():
            scan_log.scan_end = datetime.now(UTC)
            return ScanResult(
                target=str(path),
                success=False,
                errors=[f"Path does not exist: {path}"],
                scan_log=scan_log,
            )

        if path.is_file():
            result = ScanResult(target=str(path), total_files=1, scan_log=scan_log)
            result.scan_log.files_scanned.append(path.name)
            result.matches = self._scanner.scan_file(path)
        else:
            result = self._scan_directory(path, scan_log)

        # Scan git history if requested and path is a git repo
        if self.config.scan_history and (path / ".git").exists():
            history_matches = self._scan_git_history(path, result.scan_log)
            result.history_matches = history_matches

        # Validate if requested
        all_matches = result.matches + [hm.match for hm in result.history_matches]
        if self.config.validate and all_matches:
            result.validation_stats = await self._validate_matches(all_matches)

        result.scan_log.scan_end = datetime.now(UTC)
        return result

    async def scan_repo(self, url: str) -> ScanResult:
        """Scan a GitHub repository with optional git history.

        Args:
            url: Repository URL to scan.

        Returns:
            ScanResult with findings.
        """
        scan_log = ScanLog(scan_start=datetime.now(UTC))
        result = ScanResult(target=url, scan_log=scan_log)

        try:
            # Use full clone if scanning history, shallow otherwise
            shallow = not self.config.scan_history

            with GitFetcher(url=url, shallow=shallow) as fetcher:
                fetcher.clone()
                repo_path = fetcher.repo_path

                if repo_path is None:
                    result.success = False
                    result.errors.append("Failed to clone repository")
                    result.scan_log.scan_end = datetime.now(UTC)
                    return result

                # Scan the cloned directory
                local_result = await self.scan_local(repo_path)
                result.matches = local_result.matches
                result.history_matches = local_result.history_matches
                result.total_files = local_result.total_files
                result.scan_log = local_result.scan_log
                result.errors.extend(local_result.errors)
                result.validation_stats = local_result.validation_stats

        except Exception as e:
            logger.exception("Error scanning repository")
            result.success = False
            result.errors.append(str(e))

        result.scan_log.scan_end = datetime.now(UTC)
        return result

    async def scan_batch(self, targets: Sequence[str]) -> list[ScanResult]:
        """Scan multiple targets (URLs or local paths).

        Supports:
        - Multiple GitHub repository URLs
        - Multiple local paths
        - Mixed URLs and paths

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

        # Print current file matches
        self._console_reporter.print_matches(result.matches)

        # Print history matches if any
        if result.history_matches:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            console.print("\n[bold yellow]Git History Findings:[/bold yellow]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Commit", style="cyan", width=10)
            table.add_column("Date")
            table.add_column("Provider")
            table.add_column("File")
            table.add_column("Secret (redacted)")

            for hm in result.history_matches:
                table.add_row(
                    hm.commit.short_hash,
                    hm.commit.date.strftime("%Y-%m-%d"),
                    hm.match.provider,
                    hm.match.file_path,
                    hm.match.redacted_value,
                )

            console.print(table)

        # Build summary
        summary = ConsoleSummary(
            total_files=result.total_files,
            total_matches=result.total_matches,
        )
        for match in result.matches:
            summary.matches_by_provider[match.provider] = (
                summary.matches_by_provider.get(match.provider, 0) + 1
            )
        for hm in result.history_matches:
            summary.matches_by_provider[hm.match.provider] = (
                summary.matches_by_provider.get(hm.match.provider, 0) + 1
            )

        if result.validation_stats:
            summary.validated_count = result.validation_stats.validated
            summary.valid_count = result.validation_stats.valid

        self._console_reporter.print_summary(summary)

        # Print scan log summary
        if result.scan_log.files_scanned or result.scan_log.commits_scanned:
            from rich.console import Console
            from rich.panel import Panel

            console = Console()
            log_lines = [
                f"Files scanned: {len(result.scan_log.files_scanned)}",
                f"Commits scanned: {result.scan_log.commits_scanned}",
                f"Duration: {result.scan_log.duration_seconds:.2f}s",
            ]
            if result.scan_log.branches_scanned:
                log_lines.append(f"Branches: {len(result.scan_log.branches_scanned)}")
            console.print(Panel("\n".join(log_lines), title="Scan Log"))

        # Print errors
        for error in result.errors:
            self._console_reporter.print_error(error)

    def _print_json_results(self, result: ScanResult) -> None:
        """Print results as JSON with full scan log."""
        output = {
            "target": result.target,
            "success": result.success,
            "current_matches": [
                {
                    "provider": m.provider,
                    "file_path": m.file_path,
                    "line_number": m.line_number,
                    "secret_redacted": m.redacted_value,
                    "pattern_name": m.pattern_name,
                    "entropy": m.entropy,
                }
                for m in result.matches
            ],
            "history_matches": [
                {
                    "provider": hm.match.provider,
                    "file_path": hm.match.file_path,
                    "line_number": hm.match.line_number,
                    "secret_redacted": hm.match.redacted_value,
                    "commit_hash": hm.commit.hash,
                    "commit_short": hm.commit.short_hash,
                    "commit_date": hm.commit.date.isoformat(),
                    "commit_author": hm.commit.author,
                    "is_deleted": hm.is_deleted,
                }
                for hm in result.history_matches
            ],
            "summary": {
                "total_files": result.total_files,
                "total_matches": result.total_matches,
                "current_matches_count": result.current_matches_count,
                "history_matches_count": result.history_matches_count,
            },
            "scan_log": result.scan_log.to_dict(),
            "errors": result.errors,
        }
        print(json.dumps(output, indent=2, default=str))

    def _print_sarif_results(self, result: ScanResult) -> None:
        """Print results as SARIF."""
        # Combine current and history matches for SARIF
        all_matches = result.matches + [hm.match for hm in result.history_matches]
        sarif_output = self._sarif_reporter.generate_json(all_matches)
        print(sarif_output)

    def write_results(self, result: ScanResult, output_path: Path) -> None:
        """Write results to a file.

        Args:
            result: Scan result to write.
            output_path: Path to write to.
        """
        if self.config.output_format == OutputFormat.JSON:
            # Write full JSON with scan log
            output = {
                "target": result.target,
                "success": result.success,
                "current_matches": [
                    {
                        "provider": m.provider,
                        "file_path": m.file_path,
                        "line_number": m.line_number,
                        "secret_redacted": m.redacted_value,
                        "pattern_name": m.pattern_name,
                        "entropy": m.entropy,
                    }
                    for m in result.matches
                ],
                "history_matches": [
                    {
                        "provider": hm.match.provider,
                        "file_path": hm.match.file_path,
                        "commit_hash": hm.commit.hash,
                        "commit_date": hm.commit.date.isoformat(),
                    }
                    for hm in result.history_matches
                ],
                "summary": {
                    "total_files": result.total_files,
                    "total_matches": result.total_matches,
                },
                "scan_log": result.scan_log.to_dict(),
                "errors": result.errors,
            }
            output_path.write_text(json.dumps(output, indent=2, default=str))
        elif self.config.output_format == OutputFormat.SARIF:
            all_matches = result.matches + [hm.match for hm in result.history_matches]
            self._sarif_reporter.write(all_matches, output_path)
        else:
            # For table, write JSON
            self._json_reporter.write(
                result.matches,
                output_path,
                scan_target=result.target,
            )

    def write_scan_log(self, result: ScanResult, output_path: Path) -> None:
        """Write detailed scan log to a file.

        Args:
            result: Scan result with log.
            output_path: Path to write log file.
        """
        log_data = {
            "target": result.target,
            "scan_log": result.scan_log.to_dict(),
            "files_scanned": result.scan_log.files_scanned,
            "results_summary": {
                "total_files": result.total_files,
                "current_matches": result.current_matches_count,
                "history_matches": result.history_matches_count,
                "total_matches": result.total_matches,
            },
            "matches": [
                {
                    "type": "current",
                    "provider": m.provider,
                    "file": m.file_path,
                    "line": m.line_number,
                }
                for m in result.matches
            ]
            + [
                {
                    "type": "history",
                    "provider": hm.match.provider,
                    "file": hm.match.file_path,
                    "commit": hm.commit.short_hash,
                }
                for hm in result.history_matches
            ],
            "errors": result.errors,
        }
        output_path.write_text(json.dumps(log_data, indent=2, default=str))


def create_orchestrator(
    validate: bool = False,
    output_format: str = "table",
    providers: list[str] | None = None,
    verbose: bool = False,
    scan_history: bool = False,
) -> ScanOrchestrator:
    """Create a configured scan orchestrator.

    Args:
        validate: Whether to validate discovered keys.
        output_format: Output format (table, json, sarif).
        providers: List of providers to scan for.
        verbose: Whether to show verbose output.
        scan_history: Whether to scan git history (ALL branches).

    Returns:
        Configured ScanOrchestrator.
    """
    config = ScanConfig(
        validate=validate,
        output_format=OutputFormat(output_format),
        providers=providers,
        scan_history=scan_history,
        verbose=verbose,
    )
    return ScanOrchestrator(config=config)
