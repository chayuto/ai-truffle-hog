"""Unit tests for Reporter modules."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path  # noqa: TC003

from rich.console import Console

from ai_truffle_hog.core.scanner import ScanMatch
from ai_truffle_hog.reporter.console import (
    ConsoleReporter,
    ConsoleSummary,
    create_console_reporter,
)
from ai_truffle_hog.reporter.json_reporter import (
    JSONFinding,
    JSONReporter,
    create_json_reporter,
)
from ai_truffle_hog.reporter.sarif import (
    SARIF_VERSION,
    SARIFLocation,
    SARIFReporter,
    SARIFResult,
    SARIFRule,
    create_sarif_reporter,
)


def create_test_match(
    provider: str = "openai",
    line_number: int = 10,
    file_path: str = "config.py",
) -> ScanMatch:
    """Create a test ScanMatch."""
    return ScanMatch(
        provider=provider,
        pattern_name="test-pattern",
        secret_value="sk-test123456789abcdefghijklmnop",
        line_number=line_number,
        column_start=10,
        column_end=45,
        line_content='api_key = "sk-test123456789abcdefghijklmnop"',
        entropy=4.5,
        file_path=file_path,
    )


class TestSARIFLocation:
    """Tests for SARIFLocation dataclass."""

    def test_to_dict(self) -> None:
        """Test conversion to SARIF dict format."""
        location = SARIFLocation(
            file_path="config.py",
            start_line=10,
            start_column=5,
            end_line=10,
            end_column=50,
            snippet='api_key = "secret"',
        )

        result = location.to_dict()

        assert "physicalLocation" in result
        assert result["physicalLocation"]["artifactLocation"]["uri"] == "config.py"
        assert result["physicalLocation"]["region"]["startLine"] == 10
        assert "snippet" in result["physicalLocation"]["region"]

    def test_to_dict_no_snippet(self) -> None:
        """Test conversion without snippet."""
        location = SARIFLocation(
            file_path="config.py",
            start_line=10,
            start_column=5,
            end_line=10,
            end_column=50,
        )

        result = location.to_dict()

        assert "snippet" not in result["physicalLocation"]["region"]


class TestSARIFRule:
    """Tests for SARIFRule dataclass."""

    def test_to_dict(self) -> None:
        """Test conversion to SARIF dict format."""
        rule = SARIFRule(
            id="openai/api-key",
            name="OpenAI API Key",
            short_description="Exposed OpenAI key",
            full_description="Full description here",
            default_severity="error",
            tags=["security", "secrets"],
        )

        result = rule.to_dict()

        assert result["id"] == "openai/api-key"
        assert result["name"] == "OpenAI API Key"
        assert result["shortDescription"]["text"] == "Exposed OpenAI key"
        assert "fullDescription" in result
        assert "properties" in result


class TestSARIFResult:
    """Tests for SARIFResult dataclass."""

    def test_to_dict(self) -> None:
        """Test conversion to SARIF dict format."""
        location = SARIFLocation(
            file_path="config.py",
            start_line=10,
            start_column=5,
            end_line=10,
            end_column=50,
        )
        result = SARIFResult(
            rule_id="openai/api-key",
            message="Found exposed key",
            level="error",
            locations=[location],
            fingerprint="abc123",
        )

        output = result.to_dict()

        assert output["ruleId"] == "openai/api-key"
        assert output["message"]["text"] == "Found exposed key"
        assert output["level"] == "error"
        assert len(output["locations"]) == 1
        assert "fingerprints" in output


class TestSARIFReporter:
    """Tests for SARIFReporter class."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        reporter = SARIFReporter()
        assert reporter.tool_name == "ai-truffle-hog"

    def test_generate_empty(self) -> None:
        """Test generating SARIF with no matches."""
        reporter = SARIFReporter()
        sarif = reporter.generate([])

        assert sarif["version"] == SARIF_VERSION
        assert len(sarif["runs"]) == 1
        assert sarif["runs"][0]["results"] == []

    def test_generate_with_matches(self) -> None:
        """Test generating SARIF with matches."""
        reporter = SARIFReporter()
        matches = [create_test_match()]

        sarif = reporter.generate(matches)

        assert len(sarif["runs"][0]["results"]) == 1
        assert len(sarif["runs"][0]["tool"]["driver"]["rules"]) == 1

    def test_generate_json(self) -> None:
        """Test generating JSON string."""
        reporter = SARIFReporter()
        matches = [create_test_match()]

        json_str = reporter.generate_json(matches)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "version" in parsed

    def test_write(self, tmp_path: Path) -> None:
        """Test writing SARIF to file."""
        reporter = SARIFReporter()
        matches = [create_test_match()]
        output_file = tmp_path / "results.sarif"

        reporter.write(matches, output_file)

        assert output_file.exists()
        content = json.loads(output_file.read_text())
        assert content["version"] == SARIF_VERSION

    def test_multiple_providers(self) -> None:
        """Test SARIF with multiple providers."""
        reporter = SARIFReporter()
        matches = [
            create_test_match(provider="openai"),
            create_test_match(provider="anthropic"),
        ]

        sarif = reporter.generate(matches)

        # Should have 2 rules and 2 results
        assert len(sarif["runs"][0]["results"]) == 2
        assert len(sarif["runs"][0]["tool"]["driver"]["rules"]) == 2


class TestCreateSARIFReporter:
    """Tests for create_sarif_reporter factory."""

    def test_create_default(self) -> None:
        """Test creating default reporter."""
        reporter = create_sarif_reporter()
        assert isinstance(reporter, SARIFReporter)

    def test_create_custom(self) -> None:
        """Test creating with custom settings."""
        reporter = create_sarif_reporter(
            tool_name="custom-tool",
            tool_version="2.0.0",
        )
        assert reporter.tool_name == "custom-tool"
        assert reporter.tool_version == "2.0.0"


class TestJSONFinding:
    """Tests for JSONFinding dataclass."""

    def test_creation(self) -> None:
        """Test creating JSONFinding."""
        finding = JSONFinding(
            provider="openai",
            pattern_name="test",
            secret_redacted="sk-****",
            file_path="config.py",
            line_number=10,
            column_start=5,
            column_end=50,
            line_content="api = ...",
        )

        assert finding.provider == "openai"
        assert finding.validation_status is None


class TestJSONReporter:
    """Tests for JSONReporter class."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        reporter = JSONReporter()
        assert reporter.tool_name == "ai-truffle-hog"
        assert reporter.include_context

    def test_generate_empty(self) -> None:
        """Test generating JSON with no matches."""
        reporter = JSONReporter()
        result = reporter.generate([])

        assert result["total_findings"] == 0
        assert result["findings"] == []

    def test_generate_with_matches(self) -> None:
        """Test generating JSON with matches."""
        reporter = JSONReporter()
        matches = [create_test_match()]

        result = reporter.generate(matches)

        assert result["total_findings"] == 1
        assert len(result["findings"]) == 1
        assert result["findings"][0]["provider"] == "openai"

    def test_generate_json(self) -> None:
        """Test generating JSON string."""
        reporter = JSONReporter()
        matches = [create_test_match()]

        json_str = reporter.generate_json(matches)

        parsed = json.loads(json_str)
        assert "findings" in parsed

    def test_write(self, tmp_path: Path) -> None:
        """Test writing JSON to file."""
        reporter = JSONReporter()
        matches = [create_test_match()]
        output_file = tmp_path / "results.json"

        reporter.write(matches, output_file)

        assert output_file.exists()
        content = json.loads(output_file.read_text())
        assert content["total_findings"] == 1

    def test_summary_computed(self) -> None:
        """Test summary is computed correctly."""
        reporter = JSONReporter()
        matches = [
            create_test_match(provider="openai", file_path="file1.py"),
            create_test_match(provider="openai", file_path="file2.py"),
            create_test_match(provider="anthropic", file_path="file1.py"),
        ]

        result = reporter.generate(matches)

        assert result["summary"]["total_findings"] == 3
        assert result["summary"]["unique_files"] == 2
        assert result["summary"]["findings_by_provider"]["openai"] == 2
        assert result["summary"]["findings_by_provider"]["anthropic"] == 1


class TestCreateJSONReporter:
    """Tests for create_json_reporter factory."""

    def test_create_default(self) -> None:
        """Test creating default reporter."""
        reporter = create_json_reporter()
        assert isinstance(reporter, JSONReporter)
        assert reporter.include_context

    def test_create_without_context(self) -> None:
        """Test creating without context."""
        reporter = create_json_reporter(include_context=False)
        assert not reporter.include_context


class TestConsoleSummary:
    """Tests for ConsoleSummary dataclass."""

    def test_initial_values(self) -> None:
        """Test initial values."""
        summary = ConsoleSummary()
        assert summary.total_files == 0
        assert summary.total_matches == 0
        assert summary.matches_by_provider == {}

    def test_add_match(self) -> None:
        """Test adding matches."""
        summary = ConsoleSummary()
        summary.add_match("openai")
        summary.add_match("openai")
        summary.add_match("anthropic")

        assert summary.total_matches == 3
        assert summary.matches_by_provider["openai"] == 2
        assert summary.matches_by_provider["anthropic"] == 1


class TestConsoleReporter:
    """Tests for ConsoleReporter class."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        reporter = ConsoleReporter()
        assert reporter.console is not None
        assert not reporter.verbose
        assert reporter.show_context

    def test_init_with_console(self) -> None:
        """Test initialization with custom console."""
        console = Console(file=StringIO())
        reporter = ConsoleReporter(console=console)
        assert reporter.console is console

    def test_print_header(self) -> None:
        """Test printing header."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        reporter = ConsoleReporter(console=console)

        reporter.print_header("Test Header")

        # Should not raise
        assert len(output.getvalue()) > 0

    def test_print_matches_empty(self) -> None:
        """Test printing empty matches."""
        output = StringIO()
        console = Console(file=output)
        reporter = ConsoleReporter(console=console)

        reporter.print_matches([])

        assert "No secrets found" in output.getvalue()

    def test_print_matches_with_data(self) -> None:
        """Test printing matches."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        reporter = ConsoleReporter(console=console)

        matches = [create_test_match()]
        reporter.print_matches(matches)

        result = output.getvalue()
        assert "OPENAI" in result or "openai" in result.lower()

    def test_print_summary_no_matches(self) -> None:
        """Test printing summary with no matches."""
        output = StringIO()
        console = Console(file=output)
        reporter = ConsoleReporter(console=console)

        summary = ConsoleSummary(total_files=10, total_matches=0)
        reporter.print_summary(summary)

        assert "No secrets detected" in output.getvalue()

    def test_print_summary_with_matches(self) -> None:
        """Test printing summary with matches."""
        output = StringIO()
        console = Console(file=output, force_terminal=True)
        reporter = ConsoleReporter(console=console)

        summary = ConsoleSummary(
            total_files=10,
            total_matches=5,
            matches_by_provider={"openai": 3, "anthropic": 2},
        )
        reporter.print_summary(summary)

        result = output.getvalue()
        assert "5" in result  # Total matches

    def test_print_error(self) -> None:
        """Test printing error."""
        output = StringIO()
        console = Console(file=output)
        reporter = ConsoleReporter(console=console)

        reporter.print_error("Test error")

        assert "Error" in output.getvalue()

    def test_print_warning(self) -> None:
        """Test printing warning."""
        output = StringIO()
        console = Console(file=output)
        reporter = ConsoleReporter(console=console)

        reporter.print_warning("Test warning")

        assert "Warning" in output.getvalue()


class TestCreateConsoleReporter:
    """Tests for create_console_reporter factory."""

    def test_create_default(self) -> None:
        """Test creating default reporter."""
        reporter = create_console_reporter()
        assert isinstance(reporter, ConsoleReporter)
        assert not reporter.verbose

    def test_create_verbose(self) -> None:
        """Test creating verbose reporter."""
        reporter = create_console_reporter(verbose=True)
        assert reporter.verbose
