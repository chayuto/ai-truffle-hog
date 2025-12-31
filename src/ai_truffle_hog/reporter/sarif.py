"""SARIF format reporter for GitHub/GitLab integration.

This module generates SARIF (Static Analysis Results Interchange Format)
output for integration with GitHub Code Scanning, GitLab SAST, and other
compatible tools.

SARIF 2.1.0 specification: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from pathlib import Path

    from ai_truffle_hog.core.scanner import ScanMatch

# SARIF version
SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"

# Tool information
TOOL_NAME = "ai-truffle-hog"
TOOL_VERSION = "0.1.0"
TOOL_INFORMATION_URI = "https://github.com/ai-truffle-hog/ai-truffle-hog"


@dataclass
class SARIFLocation:
    """SARIF physical location representation."""

    file_path: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to SARIF location format."""
        location: dict[str, Any] = {
            "physicalLocation": {
                "artifactLocation": {"uri": self.file_path},
                "region": {
                    "startLine": self.start_line,
                    "startColumn": self.start_column,
                    "endLine": self.end_line,
                    "endColumn": self.end_column,
                },
            }
        }

        if self.snippet:
            location["physicalLocation"]["region"]["snippet"] = {"text": self.snippet}

        return location


@dataclass
class SARIFRule:
    """SARIF rule definition for a provider pattern."""

    id: str
    name: str
    short_description: str
    full_description: str = ""
    help_uri: str = ""
    default_severity: str = "error"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to SARIF rule format."""
        rule: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "shortDescription": {"text": self.short_description},
            "defaultConfiguration": {"level": self.default_severity},
        }

        if self.full_description:
            rule["fullDescription"] = {"text": self.full_description}

        if self.help_uri:
            rule["helpUri"] = self.help_uri

        if self.tags:
            rule["properties"] = {"tags": self.tags}

        return rule


@dataclass
class SARIFResult:
    """SARIF result representation of a finding."""

    rule_id: str
    message: str
    level: str
    locations: list[SARIFLocation] = field(default_factory=list)
    fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to SARIF result format."""
        result: dict[str, Any] = {
            "ruleId": self.rule_id,
            "message": {"text": self.message},
            "level": self.level,
            "locations": [loc.to_dict() for loc in self.locations],
        }

        if self.fingerprint:
            result["fingerprints"] = {"primaryLocationLineHash": self.fingerprint}

        return result


class SARIFReporter:
    """Generate SARIF format output for scan results.

    SARIF (Static Analysis Results Interchange Format) is a standard format
    for static analysis tool results, supported by GitHub Code Scanning,
    GitLab SAST, and other platforms.

    Example:
        ```python
        reporter = SARIFReporter()
        sarif_output = reporter.generate(scan_matches)
        reporter.write(scan_matches, Path("results.sarif"))
        ```
    """

    # Provider severity mappings
    SEVERITY_LEVELS: ClassVar[dict[str, str]] = {
        "openai": "error",
        "anthropic": "error",
        "huggingface": "warning",
        "cohere": "warning",
        "replicate": "warning",
        "google_gemini": "error",
        "groq": "warning",
        "langsmith": "warning",
    }

    def __init__(
        self,
        tool_name: str = TOOL_NAME,
        tool_version: str = TOOL_VERSION,
    ) -> None:
        """Initialize the SARIF reporter.

        Args:
            tool_name: Name of the tool for SARIF output.
            tool_version: Version of the tool.
        """
        self.tool_name = tool_name
        self.tool_version = tool_version
        self._rules: dict[str, SARIFRule] = {}

    def _get_or_create_rule(self, provider: str, pattern_name: str) -> SARIFRule:
        """Get or create a rule for a provider pattern.

        Args:
            provider: Provider name.
            pattern_name: Name of the pattern.

        Returns:
            SARIFRule for the provider pattern.
        """
        rule_id = f"{provider}/{pattern_name}".replace(" ", "-").lower()

        if rule_id not in self._rules:
            self._rules[rule_id] = SARIFRule(
                id=rule_id,
                name=f"{provider.upper()} API Key Exposure",
                short_description=f"Exposed {provider.upper()} API key detected",
                full_description=(
                    f"An API key for {provider.upper()} was found in the source code. "
                    "API keys should be stored in environment variables or secret managers, "
                    "not committed to version control."
                ),
                default_severity=self.SEVERITY_LEVELS.get(provider, "warning"),
                tags=["security", "secrets", "api-key", provider],
            )

        return self._rules[rule_id]

    def _match_to_result(self, match: ScanMatch) -> SARIFResult:
        """Convert a ScanMatch to a SARIF result.

        Args:
            match: The scan match to convert.

        Returns:
            SARIFResult for the match.
        """
        rule = self._get_or_create_rule(match.provider, match.pattern_name)

        location = SARIFLocation(
            file_path=match.file_path,
            start_line=match.line_number,
            start_column=match.column_start + 1,  # SARIF uses 1-based columns
            end_line=match.line_number,
            end_column=match.column_end + 1,
            snippet=match.line_content,
        )

        # Create redacted message
        message = (
            f"Exposed {match.provider.upper()} API key: {match.redacted_value}"
            if hasattr(match, "redacted_value")
            else f"Exposed {match.provider.upper()} API key detected"
        )

        # Create fingerprint from file, line, and redacted value for deduplication
        fingerprint = f"{match.file_path}:{match.line_number}:{match.provider}"

        return SARIFResult(
            rule_id=rule.id,
            message=message,
            level=rule.default_severity,
            locations=[location],
            fingerprint=fingerprint,
        )

    def generate(self, matches: list[ScanMatch]) -> dict[str, Any]:
        """Generate SARIF output from scan matches.

        Args:
            matches: List of scan matches to report.

        Returns:
            SARIF JSON structure as a dictionary.
        """
        # Reset rules for fresh generation
        self._rules = {}

        # Convert matches to results
        results = [self._match_to_result(m) for m in matches]

        # Build SARIF structure
        sarif = {
            "$schema": SARIF_SCHEMA,
            "version": SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": self.tool_name,
                            "version": self.tool_version,
                            "informationUri": TOOL_INFORMATION_URI,
                            "rules": [r.to_dict() for r in self._rules.values()],
                        }
                    },
                    "results": [r.to_dict() for r in results],
                    "invocations": [
                        {
                            "executionSuccessful": True,
                            "endTimeUtc": datetime.now(UTC).isoformat(),
                        }
                    ],
                }
            ],
        }

        return sarif

    def generate_json(
        self,
        matches: list[ScanMatch],
        pretty: bool = True,
    ) -> str:
        """Generate SARIF output as a JSON string.

        Args:
            matches: List of scan matches to report.
            pretty: Whether to format the JSON with indentation.

        Returns:
            SARIF JSON string.
        """
        sarif = self.generate(matches)
        if pretty:
            return json.dumps(sarif, indent=2, ensure_ascii=False)
        return json.dumps(sarif, ensure_ascii=False)

    def write(
        self,
        matches: list[ScanMatch],
        output_path: Path,
        pretty: bool = True,
    ) -> None:
        """Write SARIF output to a file.

        Args:
            matches: List of scan matches to report.
            output_path: Path to write the SARIF file.
            pretty: Whether to format the JSON with indentation.
        """
        sarif_json = self.generate_json(matches, pretty=pretty)
        output_path.write_text(sarif_json, encoding="utf-8")

    @property
    def rule_count(self) -> int:
        """Number of rules defined."""
        return len(self._rules)


def create_sarif_reporter(
    tool_name: str = TOOL_NAME,
    tool_version: str = TOOL_VERSION,
) -> SARIFReporter:
    """Create a SARIF reporter.

    Args:
        tool_name: Name of the tool for SARIF output.
        tool_version: Version of the tool.

    Returns:
        Configured SARIFReporter instance.
    """
    return SARIFReporter(tool_name=tool_name, tool_version=tool_version)
