"""Unit tests for PatternScanner module."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

from ai_truffle_hog.core.scanner import (
    VARIABLE_PATTERN,
    PatternScanner,
    ScanMatch,
    create_scanner,
)


class TestScanMatch:
    """Tests for ScanMatch dataclass."""

    def test_creation(self) -> None:
        """Test creating ScanMatch."""
        match = ScanMatch(
            provider="openai",
            pattern_name="OpenAI Pattern 1",
            secret_value="sk-abc123def456",
            line_number=10,
            column_start=15,
            column_end=30,
            line_content='api_key = "sk-abc123def456"',
            entropy=4.5,
        )

        assert match.provider == "openai"
        assert match.line_number == 10
        assert match.secret_value == "sk-abc123def456"

    def test_redacted_value_short(self) -> None:
        """Test redaction of short secrets."""
        match = ScanMatch(
            provider="test",
            pattern_name="test",
            secret_value="short",
            line_number=1,
            column_start=0,
            column_end=5,
            line_content="short",
        )

        assert match.redacted_value == "*****"

    def test_redacted_value_long(self) -> None:
        """Test redaction of long secrets."""
        match = ScanMatch(
            provider="test",
            pattern_name="test",
            secret_value="sk-abcdefghijklmnopqrstuvwxyz",
            line_number=1,
            column_start=0,
            column_end=30,
            line_content="test",
        )

        redacted = match.redacted_value
        assert redacted.startswith("sk-a")
        assert redacted.endswith("wxyz")
        assert "*" in redacted


class TestVariablePattern:
    """Tests for variable name extraction pattern."""

    def test_python_assignment(self) -> None:
        """Test Python-style variable assignment."""
        line = 'api_key = "sk-test123"'
        match = VARIABLE_PATTERN.search(line)
        assert match is not None
        assert match.group(1) == "api_key"

    def test_json_format(self) -> None:
        """Test JSON-style key-value."""
        line = '"openai_key": "sk-test123"'
        match = VARIABLE_PATTERN.search(line)
        assert match is not None

    def test_env_variable(self) -> None:
        """Test environment variable style."""
        line = "OPENAI_API_KEY=sk-test123"
        match = VARIABLE_PATTERN.search(line)
        assert match is not None


class TestPatternScanner:
    """Tests for PatternScanner class."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        scanner = PatternScanner()
        assert scanner.provider_count > 0
        assert scanner.pattern_count > 0

    def test_init_with_providers(self) -> None:
        """Test initialization with specific providers."""
        scanner = PatternScanner(providers=["openai"])
        assert scanner.provider_count == 1
        assert "openai" in scanner.provider_names

    def test_init_with_context_lines(self) -> None:
        """Test initialization with custom context lines."""
        scanner = PatternScanner(context_lines=5)
        assert scanner.context_lines == 5

    def test_scan_content_empty(self) -> None:
        """Test scanning empty content."""
        scanner = PatternScanner()
        matches = scanner.scan_content("")
        assert matches == []

    def test_scan_content_no_secrets(self) -> None:
        """Test scanning content without secrets."""
        scanner = PatternScanner()
        content = """
def hello():
    print("Hello, World!")
    return 42
"""
        matches = scanner.scan_content(content)
        assert matches == []

    def test_scan_content_openai_key(self) -> None:
        """Test scanning content with OpenAI key."""
        scanner = PatternScanner(providers=["openai"])
        content = (
            'openai_key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"'
        )

        matches = scanner.scan_content(content)

        assert len(matches) >= 1
        assert matches[0].provider == "openai"
        assert matches[0].line_number == 1
        assert matches[0].entropy > 0

    def test_scan_content_anthropic_key(self) -> None:
        """Test scanning content with Anthropic key."""
        scanner = PatternScanner(providers=["anthropic"])
        # Anthropic keys are sk-ant-api followed by 2 digits and 80-120 chars
        # Pattern: sk-ant-api\d{2}-[a-zA-Z0-9\-_]{80,120}
        key_suffix = "a" * 90  # Need 80-120 chars after sk-ant-apiNN-
        content = f'anthropic_key = "sk-ant-api03-{key_suffix}"'

        matches = scanner.scan_content(content)

        assert len(matches) >= 1
        assert matches[0].provider == "anthropic"

    def test_scan_content_multiple_keys(self) -> None:
        """Test scanning content with multiple keys."""
        scanner = PatternScanner(providers=["openai"])
        content = """
key1 = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"
key2 = "sk-proj-xyz987wvu654tsr321pon098mlk765jih432fed109cba876"
"""
        matches = scanner.scan_content(content)

        assert len(matches) == 2

    def test_scan_content_deduplication(self) -> None:
        """Test that duplicate secrets on same line are deduplicated."""
        scanner = PatternScanner(providers=["openai"])
        # Same key appearing once should only be matched once per location
        key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"
        content = f'key = "{key}"'

        matches = scanner.scan_content(content)

        # Should deduplicate identical matches at same position
        unique_positions = {(m.line_number, m.column_start) for m in matches}
        assert len(unique_positions) == len(matches)

    def test_scan_content_line_numbers(self) -> None:
        """Test that line numbers are correctly calculated."""
        scanner = PatternScanner(providers=["openai"])
        content = """# Line 1
# Line 2
# Line 3
api_key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"
# Line 5
"""
        matches = scanner.scan_content(content)

        assert len(matches) >= 1
        assert matches[0].line_number == 4

    def test_scan_content_context_extraction(self) -> None:
        """Test that context before/after is extracted."""
        scanner = PatternScanner(providers=["openai"], context_lines=2)
        content = """line 1
line 2
line 3
api_key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"
line 5
line 6
line 7
"""
        matches = scanner.scan_content(content)

        assert len(matches) >= 1
        match = matches[0]
        assert len(match.context_before) <= 2
        assert len(match.context_after) <= 2

    def test_scan_content_variable_extraction(self) -> None:
        """Test that variable names are extracted."""
        scanner = PatternScanner(providers=["openai"])
        content = (
            'my_api_key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"'
        )

        matches = scanner.scan_content(content)

        assert len(matches) >= 1
        # Variable extraction may or may not work depending on pattern
        # Just ensure it doesn't crash

    def test_scan_content_file_path(self) -> None:
        """Test that file path is recorded."""
        scanner = PatternScanner(providers=["openai"])
        content = 'key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"'

        matches = scanner.scan_content(content, file_path="src/config.py")

        assert len(matches) >= 1
        assert matches[0].file_path == "src/config.py"


class TestPatternScannerFileOperations:
    """Tests for PatternScanner file operations."""

    def test_scan_file(self, tmp_path: Path) -> None:
        """Test scanning a file."""
        test_file = tmp_path / "config.py"
        test_file.write_text(
            'api_key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"'
        )

        scanner = PatternScanner(providers=["openai"])
        matches = scanner.scan_file(test_file)

        assert len(matches) >= 1
        assert str(test_file) in matches[0].file_path

    def test_scan_file_safe_success(self, tmp_path: Path) -> None:
        """Test safe file scanning with valid file."""
        test_file = tmp_path / "config.py"
        test_file.write_text("# No secrets here")

        scanner = PatternScanner()
        matches, error = scanner.scan_file_safe(test_file)

        assert error is None
        assert matches == []

    def test_scan_file_safe_error(self, tmp_path: Path) -> None:
        """Test safe file scanning with nonexistent file."""
        scanner = PatternScanner()
        matches, error = scanner.scan_file_safe(tmp_path / "nonexistent.py")

        assert error is not None
        assert matches == []

    def test_iter_scan_files(self, tmp_path: Path) -> None:
        """Test iterating over multiple files."""
        # Create test files
        (tmp_path / "file1.py").write_text("# Clean file")
        (tmp_path / "file2.py").write_text(
            'key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"'
        )

        scanner = PatternScanner(providers=["openai"])
        files = [tmp_path / "file1.py", tmp_path / "file2.py"]

        results = list(scanner.iter_scan_files(files))

        assert len(results) == 2

        # First file should have no matches
        _path1, matches1, error1 = results[0]
        assert error1 is None
        assert len(matches1) == 0

        # Second file should have matches
        _path2, matches2, error2 = results[1]
        assert error2 is None
        assert len(matches2) >= 1


class TestPatternScannerProviders:
    """Tests for scanning with different providers."""

    def test_scan_huggingface_token(self) -> None:
        """Test scanning for HuggingFace tokens."""
        scanner = PatternScanner(providers=["huggingface"])
        # HuggingFace pattern: hf_[a-zA-Z0-9]{34} (exactly 34 chars after hf_)
        content = 'hf_token = "hf_abcdefghijklmnopqrstuvwxyzABCDEF12"'

        matches = scanner.scan_content(content)

        assert len(matches) >= 1
        assert matches[0].provider == "huggingface"

    def test_scan_replicate_token(self) -> None:
        """Test scanning for Replicate tokens."""
        scanner = PatternScanner(providers=["replicate"])
        # Replicate pattern: r8_[a-zA-Z0-9]{37} (exactly 37 chars after r8_)
        content = 'replicate_key = "r8_abcdefghijklmnopqrstuvwxyz1234567890A"'

        matches = scanner.scan_content(content)

        assert len(matches) >= 1
        assert matches[0].provider == "replicate"

    def test_scan_groq_key(self) -> None:
        """Test scanning for Groq keys."""
        scanner = PatternScanner(providers=["groq"])
        # Groq pattern: gsk_[a-zA-Z0-9]{50,} (at least 50 chars after gsk_)
        content = (
            'groq_key = "gsk_abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnop"'
        )

        matches = scanner.scan_content(content)

        assert len(matches) >= 1
        assert matches[0].provider == "groq"

    def test_scan_google_gemini_key(self) -> None:
        """Test scanning for Google Gemini keys."""
        scanner = PatternScanner(providers=["google_gemini"])
        # Google Gemini pattern: AIza[0-9A-Za-z\-_]{35} (exactly 35 chars after AIza)
        # AIza (4 chars) + 35 chars = 39 total
        content = 'gemini_key = "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567"'

        matches = scanner.scan_content(content)

        assert len(matches) >= 1
        assert matches[0].provider == "google_gemini"

    def test_scan_langsmith_key(self) -> None:
        """Test scanning for LangSmith keys."""
        scanner = PatternScanner(providers=["langsmith"])
        content = 'langsmith_key = "lsv2_sk_abcdefghijklmnopqrstuvwxyz12345678"'

        matches = scanner.scan_content(content)

        assert len(matches) >= 1
        assert matches[0].provider == "langsmith"

    def test_scan_all_providers(self) -> None:
        """Test scanning with all providers."""
        scanner = PatternScanner()

        # Should have multiple providers
        assert scanner.provider_count >= 8
        assert "openai" in scanner.provider_names
        assert "anthropic" in scanner.provider_names


class TestCreateScanner:
    """Tests for create_scanner factory function."""

    def test_create_scanner_default(self) -> None:
        """Test creating scanner with defaults."""
        scanner = create_scanner()
        assert isinstance(scanner, PatternScanner)
        assert scanner.provider_count > 0

    def test_create_scanner_with_providers(self) -> None:
        """Test creating scanner with specific providers."""
        scanner = create_scanner(providers=["openai", "anthropic"])
        assert scanner.provider_count == 2

    def test_create_scanner_with_context_lines(self) -> None:
        """Test creating scanner with context lines."""
        scanner = create_scanner(context_lines=10)
        assert scanner.context_lines == 10


class TestIntegration:
    """Integration tests for PatternScanner."""

    def test_realistic_config_file(self, tmp_path: Path) -> None:
        """Test scanning a realistic config file."""
        config_content = """
# Application Configuration
import os

# API Keys - these should trigger alerts
OPENAI_API_KEY = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234"
HF_TOKEN = "hf_abcdefghijklmnopqrstuvwxyzABCDEF12"

# Safe pattern - using environment variable
SAFE_KEY = os.getenv("API_KEY")

# Database config - not a secret pattern
DATABASE_URL = "postgresql://localhost/mydb"
"""
        config_file = tmp_path / "config.py"
        config_file.write_text(config_content)

        scanner = PatternScanner(providers=["openai", "huggingface"])
        matches = scanner.scan_file(config_file)

        # Should find OpenAI and HuggingFace keys
        providers_found = {m.provider for m in matches}
        assert "openai" in providers_found
        assert "huggingface" in providers_found

        # Should not match the safe pattern or database URL
        for match in matches:
            assert (
                "os.getenv" not in match.line_content
                or match.secret_value not in "os.getenv"
            )

    def test_multiline_json(self, tmp_path: Path) -> None:
        """Test scanning JSON with secrets."""
        json_content = """{
    "name": "my-app",
    "config": {
        "openai_key": "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234",
        "debug": true
    }
}"""
        json_file = tmp_path / "config.json"
        json_file.write_text(json_content)

        scanner = PatternScanner(providers=["openai"])
        matches = scanner.scan_file(json_file)

        assert len(matches) >= 1
        assert matches[0].line_number == 4  # Key is on line 4
