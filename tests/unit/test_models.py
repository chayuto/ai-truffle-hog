"""Unit tests for Pydantic models."""

from pathlib import Path

import pytest

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
            key_type="api_key",
            secret="sk-test123456789abcdef",
            file_path=Path("/test/file.py"),
            line_number=10,
            column_start=0,
            column_end=25,
        )
        assert candidate.provider == "openai"
        assert candidate.status == ValidationStatus.PENDING

    def test_full_creation(self) -> None:
        """Create with all fields."""
        candidate = SecretCandidate(
            provider="anthropic",
            key_type="api_key",
            secret="sk-ant-test123",
            file_path=Path("/test/file.py"),
            line_number=5,
            column_start=10,
            column_end=30,
            line_content='KEY = "sk-ant-test123"',
            context_before=["# Comment"],
            context_after=["# End"],
            entropy=5.5,
            status=ValidationStatus.VALID,
            validation_message="Key is active",
        )
        assert candidate.entropy == 5.5
        assert candidate.status == ValidationStatus.VALID

    def test_redacted_secret_property(self) -> None:
        """Redacted secret property works."""
        candidate = SecretCandidate(
            provider="openai",
            key_type="api_key",
            secret="sk-proj-verylongsecretkey123456789",
            file_path=Path("/test/file.py"),
            line_number=1,
            column_start=0,
            column_end=40,
        )
        redacted = candidate.redacted_secret
        assert "sk-proj-" in redacted  # Shows prefix
        assert "****" in redacted  # Has mask
        assert candidate.secret not in redacted  # Full secret hidden


class TestScanResult:
    """Tests for ScanResult model."""

    def test_creation(self) -> None:
        """Create a ScanResult."""
        result = ScanResult(
            file_path=Path("/test/file.py"),
            file_size_bytes=1024,
            lines_scanned=50,
            secrets_found=[],
            scan_duration_ms=100.5,
        )
        assert result.file_path == Path("/test/file.py")
        assert result.secrets_found == []

    def test_with_secrets(self) -> None:
        """ScanResult with found secrets."""
        secret = SecretCandidate(
            provider="openai",
            key_type="api_key",
            secret="sk-test123456",
            file_path=Path("/test/file.py"),
            line_number=1,
            column_start=0,
            column_end=15,
        )
        result = ScanResult(
            file_path=Path("/test/file.py"),
            file_size_bytes=512,
            lines_scanned=10,
            secrets_found=[secret],
            scan_duration_ms=50.0,
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
        assert len(session.results) == 0

    def test_computed_properties(self) -> None:
        """Test computed properties."""
        secret = SecretCandidate(
            provider="openai",
            key_type="api_key",
            secret="sk-test123456",
            file_path=Path("/test/file.py"),
            line_number=1,
            column_start=0,
            column_end=15,
        )
        result = ScanResult(
            file_path=Path("/test/file.py"),
            file_size_bytes=1024,
            lines_scanned=100,
            secrets_found=[secret],
            scan_duration_ms=200.0,
        )
        session = ScanSession(
            targets=["repo1", "repo2"],
            results=[result],
        )

        assert session.total_files_scanned == 1
        assert session.total_secrets_found == 1
