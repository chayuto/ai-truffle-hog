"""Unit tests for Pydantic models."""

from ai_truffle_hog.core.models import (
    ScanResult,
    ScanSession,
    SecretCandidate,
    ValidationStatus,
)


class TestValidationStatus:
    """Tests for ValidationStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """All expected statuses are defined."""
        assert ValidationStatus.PENDING is not None
        assert ValidationStatus.VALID is not None
        assert ValidationStatus.INVALID is not None
        assert ValidationStatus.ERROR is not None
        assert ValidationStatus.SKIPPED is not None


class TestSecretCandidate:
    """Tests for SecretCandidate model."""

    def test_minimal_creation(self) -> None:
        """Create with minimal required fields."""
        candidate = SecretCandidate(
            provider="openai",
            secret_value="sk-test123456789abcdef",
            file_path="/test/file.py",
            line_number=10,
        )
        assert candidate.provider == "openai"
        assert candidate.validation_status == ValidationStatus.PENDING

    def test_full_creation(self) -> None:
        """Create with all fields."""
        candidate = SecretCandidate(
            provider="anthropic",
            secret_value="sk-ant-test123",
            file_path="/test/file.py",
            line_number=5,
            column_start=10,
            column_end=30,
            context_before="# Comment",
            context_after="# End",
            entropy_score=5.5,
            validation_status=ValidationStatus.VALID,
            validation_message="Key is active",
        )
        assert candidate.entropy_score == 5.5
        assert candidate.validation_status == ValidationStatus.VALID


class TestScanResult:
    """Tests for ScanResult model."""

    def test_creation(self) -> None:
        """Create a ScanResult."""
        result = ScanResult(
            repo_url="https://github.com/test/repo",
        )
        assert result.repo_url == "https://github.com/test/repo"
        assert result.secrets_found == []

    def test_with_secrets(self) -> None:
        """ScanResult with found secrets."""
        secret = SecretCandidate(
            provider="openai",
            secret_value="sk-test123456",
            file_path="/test/file.py",
            line_number=1,
        )
        result = ScanResult(
            repo_url="https://github.com/test/repo",
            files_scanned=10,
            secrets_found=[secret],
        )
        assert len(result.secrets_found) == 1


class TestScanSession:
    """Tests for ScanSession model."""

    def test_creation(self) -> None:
        """Create a ScanSession."""
        session = ScanSession(
            targets=["https://github.com/user/repo"],
        )
        assert session.session_id is not None

    def test_with_results(self) -> None:
        """Test ScanSession with results."""
        secret = SecretCandidate(
            provider="openai",
            secret_value="sk-test123456",
            file_path="/test/file.py",
            line_number=1,
        )
        result = ScanResult(
            repo_url="https://github.com/test/repo",
            files_scanned=100,
            secrets_found=[secret],
        )
        session = ScanSession(
            targets=["repo1", "repo2"],
            results=[result],
        )

        assert len(session.results) == 1
        assert session.results[0].secrets_count == 1
