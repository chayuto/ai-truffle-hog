"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from ai_truffle_hog.core.models import SecretCandidate, ValidationStatus
from ai_truffle_hog.providers.registry import ProviderRegistry


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file_with_secrets(temp_dir: Path) -> Path:
    """Create a sample file containing mock API keys."""
    file_path = temp_dir / "sample.py"
    content = '''"""Sample Python file with secrets."""

# OpenAI API keys (test patterns)
OPENAI_KEY = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
LEGACY_OPENAI = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz5"

# Anthropic API key (test pattern)
ANTHROPIC_API_KEY = "sk-ant-api03-abc123def456ghi789jkl012mno345pqr678stu901vwx234yzABC"

# Google AI (test pattern)
GOOGLE_AI_KEY = "AIzaSyAbc123def456ghi789jkl012mno345pqr67"

# Not a secret
REGULAR_VALUE = "hello_world"
'''
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_secret_candidate() -> SecretCandidate:
    """Create a sample SecretCandidate for testing."""
    return SecretCandidate(
        provider="openai",
        key_type="api_key",
        secret="sk-proj-test123456789abcdefghijklmnopqrstuvwxyz0123456789",
        file_path=Path("/test/sample.py"),
        line_number=5,
        column_start=14,
        column_end=67,
        line_content='OPENAI_KEY = "sk-proj-test123456789abcdef..."',
        context_before=["", "# API Configuration", ""],
        context_after=["", "# End of config", ""],
        entropy=5.2,
        status=ValidationStatus.PENDING,
    )


@pytest.fixture
def provider_registry() -> ProviderRegistry:
    """Get a fresh provider registry for testing."""
    return ProviderRegistry()


@pytest.fixture
def mock_repo_path(temp_dir: Path) -> Path:
    """Create a mock repository structure."""
    # Create basic repo structure
    (temp_dir / ".git").mkdir()
    (temp_dir / "src").mkdir()

    # Create sample files
    (temp_dir / "README.md").write_text("# Test Repo\n")
    (temp_dir / ".env").write_text('SECRET_KEY="sk-test-123"\n')
    (temp_dir / "src" / "main.py").write_text(
        '''"""Main module."""

API_KEY = "sk-proj-abc123xyz789"

def main():
    pass
'''
    )

    return temp_dir
