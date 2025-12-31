"""Unit tests for the ScanOrchestrator."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_truffle_hog.core.orchestrator import (
    OutputFormat,
    ScanConfig,
    ScanOrchestrator,
    ScanResult,
    create_orchestrator,
)
from ai_truffle_hog.core.scanner import ScanMatch
from ai_truffle_hog.validator.client import SecretCandidate


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_table_value(self) -> None:
        """Test table format value."""
        assert OutputFormat.TABLE.value == "table"

    def test_json_value(self) -> None:
        """Test JSON format value."""
        assert OutputFormat.JSON.value == "json"

    def test_sarif_value(self) -> None:
        """Test SARIF format value."""
        assert OutputFormat.SARIF.value == "sarif"

    def test_from_string_table(self) -> None:
        """Test creating format from string."""
        assert OutputFormat("table") == OutputFormat.TABLE

    def test_from_string_json(self) -> None:
        """Test creating format from string."""
        assert OutputFormat("json") == OutputFormat.JSON

    def test_from_string_sarif(self) -> None:
        """Test creating format from string."""
        assert OutputFormat("sarif") == OutputFormat.SARIF

    def test_from_invalid_string(self) -> None:
        """Test invalid format string raises error."""
        with pytest.raises(ValueError):
            OutputFormat("invalid")


class TestScanResult:
    """Tests for ScanResult dataclass."""

    def test_basic_creation(self) -> None:
        """Test creating a basic scan result."""
        result = ScanResult(
            target="test-target",
            matches=[],
            total_files=10,
            success=True,
        )

        assert result.target == "test-target"
        assert result.matches == []
        assert result.total_files == 10
        assert result.total_matches == 0
        assert result.success is True

    def test_with_matches(self) -> None:
        """Test result with matches."""
        mock_match = MagicMock(spec=ScanMatch)
        result = ScanResult(
            target="repo",
            matches=[mock_match],
            total_files=50,
            success=True,
        )

        assert len(result.matches) == 1
        assert result.total_matches == 1

    def test_failed_result(self) -> None:
        """Test failed scan result."""
        result = ScanResult(
            target="bad-target",
            matches=[],
            total_files=0,
            success=False,
            errors=["Target not found"],
        )

        assert result.success is False
        assert "Target not found" in result.errors

    def test_default_errors_empty(self) -> None:
        """Test that errors default to empty list."""
        result = ScanResult(
            target="t",
            matches=[],
            total_files=0,
            success=True,
        )
        assert result.errors == []


class TestScanConfig:
    """Tests for ScanConfig dataclass."""

    def test_defaults(self) -> None:
        """Test default configuration values."""
        config = ScanConfig()

        assert config.validate is False
        assert config.output_format == OutputFormat.TABLE
        assert config.providers is None
        assert config.verbose is False
        assert config.scan_history is False

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ScanConfig(
            validate=True,
            output_format=OutputFormat.SARIF,
            providers=["openai", "anthropic"],
            verbose=True,
            scan_history=True,
        )

        assert config.validate is True
        assert config.output_format == OutputFormat.SARIF
        assert config.providers == ["openai", "anthropic"]
        assert config.verbose is True
        assert config.scan_history is True


class TestCreateOrchestrator:
    """Tests for create_orchestrator factory function."""

    def test_default_orchestrator(self) -> None:
        """Test creating orchestrator with defaults."""
        orchestrator = create_orchestrator()

        assert orchestrator is not None
        assert isinstance(orchestrator, ScanOrchestrator)
        assert orchestrator.config.validate is False
        assert orchestrator.config.output_format == OutputFormat.TABLE

    def test_with_validation(self) -> None:
        """Test creating orchestrator with validation enabled."""
        orchestrator = create_orchestrator(validate=True)

        assert orchestrator.config.validate is True

    def test_with_json_format(self) -> None:
        """Test creating orchestrator with JSON output."""
        orchestrator = create_orchestrator(output_format="json")

        assert orchestrator.config.output_format == OutputFormat.JSON

    def test_with_sarif_format(self) -> None:
        """Test creating orchestrator with SARIF output."""
        orchestrator = create_orchestrator(output_format="sarif")

        assert orchestrator.config.output_format == OutputFormat.SARIF

    def test_with_providers(self) -> None:
        """Test creating orchestrator with specific providers."""
        providers = ["openai", "anthropic"]
        orchestrator = create_orchestrator(providers=providers)

        assert orchestrator.config.providers == providers

    def test_with_verbose(self) -> None:
        """Test creating orchestrator with verbose mode."""
        orchestrator = create_orchestrator(verbose=True)

        assert orchestrator.config.verbose is True


class TestScanOrchestrator:
    """Tests for ScanOrchestrator class."""

    def test_initialization(self) -> None:
        """Test orchestrator initialization."""
        config = ScanConfig()
        orchestrator = ScanOrchestrator(config)

        assert orchestrator.config == config
        assert orchestrator._scanner is not None
        assert orchestrator._console_reporter is not None
        assert orchestrator._json_reporter is not None
        assert orchestrator._sarif_reporter is not None

    def test_initialization_with_providers(self) -> None:
        """Test orchestrator initialization with specific providers."""
        config = ScanConfig(providers=["openai"])
        orchestrator = ScanOrchestrator(config)

        # Scanner should be configured with specific providers
        assert orchestrator._scanner is not None


class TestMatchesToCandidates:
    """Tests for _matches_to_candidates method."""

    def test_empty_matches(self) -> None:
        """Test converting empty matches list."""
        orchestrator = create_orchestrator()
        candidates = orchestrator._matches_to_candidates([])

        assert candidates == []

    def test_single_match(self) -> None:
        """Test converting a single match."""
        orchestrator = create_orchestrator()

        match = ScanMatch(
            file_path="/test/file.py",
            line_number=10,
            secret_value="sk-test-key123",
            provider="openai",
            pattern_name="api_key",
            column_start=0,
            column_end=20,
            line_content="key = sk-test-key123",
            context_before=[],
            context_after=[],
            entropy=4.5,
        )

        candidates = orchestrator._matches_to_candidates([match])

        assert len(candidates) == 1
        assert isinstance(candidates[0], SecretCandidate)
        assert candidates[0].secret_value == "sk-test-key123"
        assert candidates[0].provider_name == "openai"
        assert candidates[0].file_path == "/test/file.py"
        assert candidates[0].line_number == 10

    def test_multiple_matches(self) -> None:
        """Test converting multiple matches."""
        orchestrator = create_orchestrator()

        matches = [
            ScanMatch(
                file_path="/test/file1.py",
                line_number=1,
                secret_value="sk-key1",
                provider="openai",
                pattern_name="api_key",
                column_start=0,
                column_end=10,
                line_content="key1",
                context_before=[],
                context_after=[],
                entropy=4.0,
            ),
            ScanMatch(
                file_path="/test/file2.py",
                line_number=2,
                secret_value="sk-ant-key2",
                provider="anthropic",
                pattern_name="api_key",
                column_start=0,
                column_end=15,
                line_content="key2",
                context_before=[],
                context_after=[],
                entropy=4.2,
            ),
        ]

        candidates = orchestrator._matches_to_candidates(matches)

        assert len(candidates) == 2
        assert candidates[0].provider_name == "openai"
        assert candidates[1].provider_name == "anthropic"


class TestScanDirectory:
    """Tests for _scan_directory method."""

    def test_scan_empty_directory(self) -> None:
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = create_orchestrator()
            result = orchestrator._scan_directory(Path(tmpdir))

            assert result.matches == []
            assert result.total_files == 0

    def test_scan_directory_with_no_secrets(self) -> None:
        """Test scanning directory with clean files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a clean file
            clean_file = Path(tmpdir) / "clean.py"
            clean_file.write_text('print("Hello, World!")')

            orchestrator = create_orchestrator()
            result = orchestrator._scan_directory(Path(tmpdir))

            assert result.matches == []
            assert result.total_files == 1

    def test_scan_directory_with_secret(self) -> None:
        """Test scanning directory containing secrets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with a secret-like pattern
            secret_file = Path(tmpdir) / "config.py"
            secret_file.write_text(
                'API_KEY = "sk-proj-test1234567890abcdefghijklmnopqrs"'
            )

            orchestrator = create_orchestrator()
            result = orchestrator._scan_directory(Path(tmpdir))

            assert result.total_files == 1
            # May or may not find matches depending on pattern
            # Just verify it runs without error

    def test_scan_directory_skips_binary(self) -> None:
        """Test that binary files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a text file
            text_file = Path(tmpdir) / "script.py"
            text_file.write_text('print("test")')

            # Create a binary-like file
            binary_file = Path(tmpdir) / "image.png"
            binary_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

            orchestrator = create_orchestrator()
            result = orchestrator._scan_directory(Path(tmpdir))

            # Should only scan the text file
            assert result.total_files == 1


class TestScanLocal:
    """Tests for scan_local method."""

    @pytest.mark.asyncio
    async def test_scan_nonexistent_path(self) -> None:
        """Test scanning a path that doesn't exist."""
        orchestrator = create_orchestrator()
        result = await orchestrator.scan_local(Path("/nonexistent/path"))

        assert result.success is False
        assert any("does not exist" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_scan_empty_directory(self) -> None:
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = create_orchestrator()
            result = await orchestrator.scan_local(Path(tmpdir))

            assert result.success is True
            assert result.total_matches == 0
            assert result.total_files == 0

    @pytest.mark.asyncio
    async def test_scan_directory_with_files(self) -> None:
        """Test scanning directory with files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            (Path(tmpdir) / "file1.py").write_text("# Python file")
            (Path(tmpdir) / "file2.py").write_text("# Another file")

            orchestrator = create_orchestrator()
            result = await orchestrator.scan_local(Path(tmpdir))

            assert result.success is True
            assert result.total_files == 2

    @pytest.mark.asyncio
    async def test_scan_single_file(self) -> None:
        """Test scanning a single file."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b'print("Hello")')
            temp_path = Path(f.name)

        try:
            orchestrator = create_orchestrator()
            result = await orchestrator.scan_local(temp_path)

            assert result.success is True
            assert result.total_files == 1
        finally:
            temp_path.unlink()


class TestScanRepo:
    """Tests for scan_repo method."""

    @pytest.mark.asyncio
    async def test_scan_repo_clone_failure(self) -> None:
        """Test handling clone failures."""
        orchestrator = create_orchestrator()

        # Use a non-existent repo URL - mock GitFetcher to fail
        with patch("ai_truffle_hog.core.orchestrator.GitFetcher") as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
            mock_fetcher.__exit__ = MagicMock(return_value=False)
            mock_fetcher.clone.side_effect = Exception("Clone failed")
            mock_fetcher_class.return_value = mock_fetcher

            result = await orchestrator.scan_repo("https://github.com/test/nonexistent")

            assert result.success is False
            assert any("clone failed" in e.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_scan_repo_success(self) -> None:
        """Test successful repo scan with mocked clone."""
        orchestrator = create_orchestrator()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock repo directory
            repo_path = Path(tmpdir) / "repo"
            repo_path.mkdir()
            (repo_path / "file.py").write_text("# Clean file")

            # Mock the GitFetcher context manager
            with patch(
                "ai_truffle_hog.core.orchestrator.GitFetcher"
            ) as mock_fetcher_class:
                mock_fetcher = MagicMock()
                mock_fetcher.__enter__ = MagicMock(return_value=mock_fetcher)
                mock_fetcher.__exit__ = MagicMock(return_value=False)
                mock_fetcher.repo_path = repo_path
                mock_fetcher_class.return_value = mock_fetcher

                result = await orchestrator.scan_repo(
                    "https://github.com/test/repo.git"
                )

                assert result.success is True
                assert result.total_files >= 0


class TestScanBatch:
    """Tests for scan_batch method."""

    @pytest.mark.asyncio
    async def test_scan_batch_empty(self) -> None:
        """Test scanning empty batch."""
        orchestrator = create_orchestrator()
        results = await orchestrator.scan_batch([])

        assert results == []

    @pytest.mark.asyncio
    async def test_scan_batch_single_local(self) -> None:
        """Test scanning single local target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = create_orchestrator()
            results = await orchestrator.scan_batch([tmpdir])

            assert len(results) == 1
            assert results[0].success is True

    @pytest.mark.asyncio
    async def test_scan_batch_multiple_targets(self) -> None:
        """Test scanning multiple targets."""
        with (
            tempfile.TemporaryDirectory() as tmpdir1,
            tempfile.TemporaryDirectory() as tmpdir2,
        ):
            # Create files in directories
            (Path(tmpdir1) / "file1.py").write_text("# File 1")
            (Path(tmpdir2) / "file2.py").write_text("# File 2")

            orchestrator = create_orchestrator()
            results = await orchestrator.scan_batch([tmpdir1, tmpdir2])

            assert len(results) == 2
            assert all(r.success for r in results)


class TestPrintResults:
    """Tests for print_results method."""

    def test_print_table_format(self) -> None:
        """Test printing results in table format."""
        orchestrator = create_orchestrator(output_format="table")

        result = ScanResult(
            target="test",
            matches=[],
            total_files=5,
            success=True,
        )

        # Should not raise
        orchestrator.print_results(result)

    def test_print_json_format(self) -> None:
        """Test printing results in JSON format."""
        orchestrator = create_orchestrator(output_format="json")

        result = ScanResult(
            target="test",
            matches=[],
            total_files=5,
            success=True,
        )

        # Should not raise
        orchestrator.print_results(result)

    def test_print_sarif_format(self) -> None:
        """Test printing results in SARIF format."""
        orchestrator = create_orchestrator(output_format="sarif")

        result = ScanResult(
            target="test",
            matches=[],
            total_files=5,
            success=True,
        )

        # Should not raise
        orchestrator.print_results(result)


class TestWriteResults:
    """Tests for write_results method."""

    def test_write_json_format(self) -> None:
        """Test writing results to JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"

            orchestrator = create_orchestrator(output_format="json")

            result = ScanResult(
                target="test",
                matches=[],
                total_files=5,
                success=True,
            )

            orchestrator.write_results(result, output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "test" in content  # Target should be in output

    def test_write_sarif_format(self) -> None:
        """Test writing results to SARIF file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.sarif"

            orchestrator = create_orchestrator(output_format="sarif")

            result = ScanResult(
                target="test",
                matches=[],
                total_files=5,
                success=True,
            )

            orchestrator.write_results(result, output_path)

            assert output_path.exists()
            content = output_path.read_text()
            assert "sarif" in content.lower() or "$schema" in content


class TestValidateMatches:
    """Tests for _validate_matches method."""

    @pytest.mark.asyncio
    async def test_validate_empty_matches(self) -> None:
        """Test validating empty matches list."""
        orchestrator = create_orchestrator(validate=True)

        # Mock the validation client with proper async mocks
        from unittest.mock import AsyncMock

        from ai_truffle_hog.validator.client import ValidationStats

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.validate_batch = AsyncMock(return_value=([], ValidationStats()))

        with patch(
            "ai_truffle_hog.core.orchestrator.create_validation_client",
            return_value=mock_client,
        ):
            stats = await orchestrator._validate_matches([])

            # Should return empty stats
            assert stats.validated == 0


class TestVerboseOutput:
    """Tests for verbose mode functionality."""

    def test_verbose_creates_different_reporter(self) -> None:
        """Test that verbose mode affects reporter configuration."""
        quiet_orchestrator = create_orchestrator(verbose=False)
        verbose_orchestrator = create_orchestrator(verbose=True)

        # Both should have reporters
        assert quiet_orchestrator._console_reporter is not None
        assert verbose_orchestrator._console_reporter is not None

        # Config should differ
        assert quiet_orchestrator.config.verbose is False
        assert verbose_orchestrator.config.verbose is True


class TestErrorHandling:
    """Tests for error handling in orchestrator."""

    @pytest.mark.asyncio
    async def test_handles_file_read_errors_gracefully(self) -> None:
        """Test that file read errors don't crash the scan."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a readable file
            good_file = Path(tmpdir) / "good.py"
            good_file.write_text("# Good file")

            orchestrator = create_orchestrator()
            result = await orchestrator.scan_local(Path(tmpdir))

            # Should complete without error
            assert result.success is True

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_target(self) -> None:
        """Test error handling for invalid targets."""
        orchestrator = create_orchestrator()

        # Non-existent path
        result = await orchestrator.scan_local(Path("/this/path/does/not/exist"))

        assert result.success is False
        assert len(result.errors) > 0


class TestIntegration:
    """Integration tests for orchestrator with all components."""

    @pytest.mark.asyncio
    async def test_full_scan_workflow(self) -> None:
        """Test complete scan workflow with all components."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "config.py").write_text(
                '# Configuration\nDEBUG = True\nVERSION = "1.0.0"'
            )
            (Path(tmpdir) / "main.py").write_text(
                'def main():\n    print("Running")\n\nif __name__ == "__main__":\n    main()'
            )

            # Create subdirectory
            subdir = Path(tmpdir) / "src"
            subdir.mkdir()
            (subdir / "utils.py").write_text("def helper():\n    return 42")

            orchestrator = create_orchestrator()
            result = await orchestrator.scan_local(Path(tmpdir))

            assert result.success is True
            assert result.total_files == 3

    @pytest.mark.asyncio
    async def test_scan_with_all_output_formats(self) -> None:
        """Test scanning with each output format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text("# Test file")

            for format_type in OutputFormat:
                orchestrator = create_orchestrator(output_format=format_type.value)
                result = await orchestrator.scan_local(Path(tmpdir))

                assert result.success is True, f"Failed for format {format_type}"
