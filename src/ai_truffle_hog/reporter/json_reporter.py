"""JSON output reporter.

This module provides JSON serialization functionality for
exporting scan results to files.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from ai_truffle_hog.core.scanner import ScanMatch


@dataclass
class JSONFinding:
    """JSON representation of a scan finding.

    Attributes:
        provider: Provider name.
        pattern_name: Name of the matched pattern.
        secret_redacted: Redacted secret value.
        file_path: Path to the file.
        line_number: Line number in the file.
        column_start: Start column of the secret.
        column_end: End column of the secret.
        line_content: Content of the line.
        entropy: Shannon entropy of the secret.
        context_before: Lines before the match.
        context_after: Lines after the match.
        validation_status: Optional validation status.
    """

    provider: str
    pattern_name: str
    secret_redacted: str
    file_path: str
    line_number: int
    column_start: int
    column_end: int
    line_content: str
    entropy: float | None = None
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    validation_status: str | None = None


@dataclass
class JSONReport:
    """JSON report structure.

    Attributes:
        tool: Name of the scanning tool.
        version: Tool version.
        timestamp: When the scan was performed.
        scan_target: Target that was scanned.
        total_findings: Number of findings.
        findings: List of findings.
        summary: Summary statistics.
    """

    tool: str
    version: str
    timestamp: str
    scan_target: str
    total_findings: int
    findings: list[JSONFinding]
    summary: dict[str, Any] = field(default_factory=dict)


class JSONReporter:
    """JSON reporter for scan results.

    Provides structured JSON output suitable for:
    - Machine parsing
    - API responses
    - Data storage
    - Integration with other tools

    Example:
        ```python
        reporter = JSONReporter()
        json_output = reporter.generate(matches)
        reporter.write(matches, Path("results.json"))
        ```
    """

    def __init__(
        self,
        tool_name: str = "ai-truffle-hog",
        tool_version: str = "0.1.0",
        include_context: bool = True,
    ) -> None:
        """Initialize the JSON reporter.

        Args:
            tool_name: Name of the tool.
            tool_version: Version of the tool.
            include_context: Whether to include context lines.
        """
        self.tool_name = tool_name
        self.tool_version = tool_version
        self.include_context = include_context

    def _match_to_finding(self, match: ScanMatch) -> JSONFinding:
        """Convert a ScanMatch to JSONFinding.

        Args:
            match: The scan match to convert.

        Returns:
            JSONFinding for the match.
        """
        return JSONFinding(
            provider=match.provider,
            pattern_name=match.pattern_name,
            secret_redacted=match.redacted_value,
            file_path=match.file_path,
            line_number=match.line_number,
            column_start=match.column_start,
            column_end=match.column_end,
            line_content=match.line_content,
            entropy=match.entropy,
            context_before=list(match.context_before) if self.include_context else [],
            context_after=list(match.context_after) if self.include_context else [],
        )

    def _compute_summary(
        self,
        matches: list[ScanMatch],
    ) -> dict[str, Any]:
        """Compute summary statistics.

        Args:
            matches: List of scan matches.

        Returns:
            Summary dictionary.
        """
        providers: dict[str, int] = {}
        files: set[str] = set()

        for match in matches:
            providers[match.provider] = providers.get(match.provider, 0) + 1
            files.add(match.file_path)

        return {
            "total_findings": len(matches),
            "unique_files": len(files),
            "findings_by_provider": providers,
        }

    def generate(
        self,
        matches: list[ScanMatch],
        scan_target: str = "",
    ) -> dict[str, Any]:
        """Generate JSON output from scan matches.

        Args:
            matches: List of scan matches to report.
            scan_target: Description of what was scanned.

        Returns:
            JSON structure as a dictionary.
        """
        findings = [self._match_to_finding(m) for m in matches]
        summary = self._compute_summary(matches)

        report = JSONReport(
            tool=self.tool_name,
            version=self.tool_version,
            timestamp=datetime.now(UTC).isoformat(),
            scan_target=scan_target,
            total_findings=len(findings),
            findings=findings,
            summary=summary,
        )

        # Convert to dict, handling nested dataclasses
        return {
            "tool": report.tool,
            "version": report.version,
            "timestamp": report.timestamp,
            "scan_target": report.scan_target,
            "total_findings": report.total_findings,
            "findings": [asdict(f) for f in report.findings],
            "summary": report.summary,
        }

    def generate_json(
        self,
        matches: list[ScanMatch],
        scan_target: str = "",
        pretty: bool = True,
    ) -> str:
        """Generate JSON output as a string.

        Args:
            matches: List of scan matches to report.
            scan_target: Description of what was scanned.
            pretty: Whether to format the JSON with indentation.

        Returns:
            JSON string.
        """
        data = self.generate(matches, scan_target)
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False)

    def write(
        self,
        matches: list[ScanMatch],
        output_path: Path,
        scan_target: str = "",
        pretty: bool = True,
    ) -> None:
        """Write JSON output to a file.

        Args:
            matches: List of scan matches to report.
            output_path: Path to write the JSON file.
            scan_target: Description of what was scanned.
            pretty: Whether to format the JSON with indentation.
        """
        json_str = self.generate_json(matches, scan_target, pretty)
        output_path.write_text(json_str, encoding="utf-8")


def create_json_reporter(
    include_context: bool = True,
) -> JSONReporter:
    """Create a JSON reporter.

    Args:
        include_context: Whether to include context lines.

    Returns:
        Configured JSONReporter instance.
    """
    return JSONReporter(include_context=include_context)
