"""Unit tests for GitFetcher module."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path  # noqa: TC003
from unittest.mock import MagicMock, patch

import pytest
from git.exc import InvalidGitRepositoryError

from ai_truffle_hog.fetcher.git import (
    CommitInfo,
    FileChange,
    GitFetcher,
    GitHistoryScanner,
    clone_repository,
    is_git_repository,
)


class TestCommitInfo:
    """Tests for CommitInfo dataclass."""

    def test_creation(self) -> None:
        """Test creating CommitInfo."""
        commit = CommitInfo(
            hash="abc123def456",
            short_hash="abc123de",
            author="Test Author",
            author_email="test@example.com",
            date=datetime(2024, 1, 1, 12, 0, 0),
            message="Test commit",
            is_merge=False,
        )

        assert commit.hash == "abc123def456"
        assert commit.short_hash == "abc123de"
        assert commit.author == "Test Author"
        assert commit.is_merge is False

    def test_from_pydriller_commit(self) -> None:
        """Test creating CommitInfo from PyDriller commit."""
        mock_commit = MagicMock()
        mock_commit.hash = "abc123def456789"
        mock_commit.author.name = "Test Author"
        mock_commit.author.email = "test@example.com"
        mock_commit.author_date = datetime(2024, 1, 1, 12, 0, 0)
        mock_commit.msg = "Test commit message\n"
        mock_commit.merge = False

        commit_info = CommitInfo.from_pydriller_commit(mock_commit)

        assert commit_info.hash == "abc123def456789"
        assert commit_info.short_hash == "abc123de"
        assert commit_info.author == "Test Author"
        assert commit_info.message == "Test commit message"


class TestFileChange:
    """Tests for FileChange dataclass."""

    def test_creation(self) -> None:
        """Test creating FileChange."""
        change = FileChange(
            path="src/main.py",
            old_path=None,
            content="print('hello')",
            diff="+ print('hello')",
            added_lines=1,
            deleted_lines=0,
            is_added=True,
        )

        assert change.path == "src/main.py"
        assert change.is_added is True
        assert change.is_deleted is False

    def test_from_pydriller_modification(self) -> None:
        """Test creating FileChange from PyDriller modification."""
        mock_mod = MagicMock()
        mock_mod.new_path = "src/main.py"
        mock_mod.old_path = "src/main.py"
        mock_mod.source_code = "print('hello')"
        mock_mod.diff = "+ print('hello')"
        mock_mod.added_lines = 1
        mock_mod.deleted_lines = 0
        mock_mod.change_type.name = "ADD"

        change = FileChange.from_pydriller_modification(mock_mod)

        assert change.path == "src/main.py"
        assert change.is_added is True
        assert change.content == "print('hello')"


class TestGitFetcher:
    """Tests for GitFetcher class."""

    def test_init_https_url(self) -> None:
        """Test initializing with HTTPS URL."""
        fetcher = GitFetcher(url="https://github.com/user/repo.git")
        assert fetcher.url == "https://github.com/user/repo.git"
        assert fetcher.repo_name == "repo"

    def test_init_ssh_url(self) -> None:
        """Test initializing with SSH URL."""
        fetcher = GitFetcher(url="git@github.com:user/myrepo.git")
        assert fetcher.repo_name == "myrepo"

    def test_init_invalid_url(self) -> None:
        """Test initializing with invalid URL raises error."""
        with pytest.raises(ValueError, match="Invalid git repository"):
            GitFetcher(url="not-a-valid-url")

    def test_repo_name_extraction_https(self) -> None:
        """Test repo name extraction from HTTPS URL."""
        fetcher = GitFetcher(url="https://github.com/user/my-project.git")
        assert fetcher.repo_name == "my-project"

    def test_repo_name_extraction_ssh(self) -> None:
        """Test repo name extraction from SSH URL."""
        fetcher = GitFetcher(url="git@github.com:org/test-repo.git")
        assert fetcher.repo_name == "test-repo"

    def test_context_manager(self, tmp_path: Path) -> None:
        """Test context manager usage."""
        # Create a minimal git repo for testing
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        with GitFetcher(url=str(repo_path)) as fetcher:
            assert fetcher is not None

    def test_cleanup_removes_temp_dir(self, tmp_path: Path) -> None:
        """Test that cleanup removes temporary directory."""
        fetcher = GitFetcher(url="https://github.com/user/repo.git")
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        fetcher._temp_dir = temp_dir
        fetcher.repo_path = temp_dir / "repo"
        fetcher.repo_path.mkdir()

        fetcher.cleanup()

        # After cleanup, temp_dir should be removed and _temp_dir should be None
        assert not temp_dir.exists()
        assert fetcher._temp_dir is None
        assert fetcher.repo_path is None


class TestGitFetcherWithLocalRepo:
    """Tests for GitFetcher with actual local git operations."""

    @pytest.fixture
    def local_git_repo(self, tmp_path: Path) -> Path:
        """Create a local git repository for testing."""
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Configure git for commits
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create initial commit
        (repo_path / "README.md").write_text("# Test Repo")
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        return repo_path

    def test_open_local(self, local_git_repo: Path) -> None:
        """Test opening a local repository."""
        fetcher = GitFetcher(url=str(local_git_repo))
        path = fetcher.open_local(local_git_repo)

        assert path == local_git_repo.resolve()
        assert fetcher.repo_path == local_git_repo.resolve()

    def test_open_local_not_git_repo(self, tmp_path: Path) -> None:
        """Test opening a non-git directory raises error."""
        fetcher = GitFetcher(url="https://github.com/user/repo.git")

        with pytest.raises(InvalidGitRepositoryError):
            fetcher.open_local(tmp_path)

    def test_get_head_commit(self, local_git_repo: Path) -> None:
        """Test getting HEAD commit hash."""
        fetcher = GitFetcher(url=str(local_git_repo))
        fetcher.open_local(local_git_repo)

        head = fetcher.get_head_commit()

        assert len(head) == 40  # Full SHA
        assert all(c in "0123456789abcdef" for c in head)

    def test_get_head_commit_not_cloned(self) -> None:
        """Test get_head_commit raises if not cloned."""
        fetcher = GitFetcher(url="https://github.com/user/repo.git")

        with pytest.raises(ValueError, match="not cloned"):
            fetcher.get_head_commit()

    def test_get_branch(self, local_git_repo: Path) -> None:
        """Test getting current branch name."""
        fetcher = GitFetcher(url=str(local_git_repo))
        fetcher.open_local(local_git_repo)

        branch = fetcher.get_branch()

        # Could be 'main' or 'master' depending on git config
        assert branch in ("main", "master")


class TestGitHistoryScanner:
    """Tests for GitHistoryScanner class."""

    @pytest.fixture
    def repo_with_history(self, tmp_path: Path) -> Path:
        """Create a git repository with multiple commits."""
        repo_path = tmp_path / "history-repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Commit 1: Add file
        (repo_path / "file1.py").write_text("print('hello')")
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add file1"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Commit 2: Modify file
        (repo_path / "file1.py").write_text("print('hello world')")
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Modify file1"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Commit 3: Add another file
        (repo_path / "file2.py").write_text("x = 1")
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add file2"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        return repo_path

    def test_init_valid_repo(self, repo_with_history: Path) -> None:
        """Test initializing with valid repository."""
        scanner = GitHistoryScanner(repo_with_history)
        assert scanner.repo_path == repo_with_history.resolve()

    def test_init_invalid_repo(self, tmp_path: Path) -> None:
        """Test initializing with non-git directory raises error."""
        with pytest.raises(InvalidGitRepositoryError):
            GitHistoryScanner(tmp_path)

    def test_iter_commits(self, repo_with_history: Path) -> None:
        """Test iterating over commits."""
        scanner = GitHistoryScanner(repo_with_history)
        commits = list(scanner.iter_commits())

        assert len(commits) == 3
        assert all(isinstance(c, CommitInfo) for c in commits)

    def test_iter_commits_with_changes(self, repo_with_history: Path) -> None:
        """Test iterating over commits with file changes."""
        scanner = GitHistoryScanner(repo_with_history)
        results = list(scanner.iter_commits_with_changes())

        assert len(results) == 3

        # Check structure
        for commit, changes in results:
            assert isinstance(commit, CommitInfo)
            assert isinstance(changes, list)
            assert all(isinstance(c, FileChange) for c in changes)

    def test_iter_all_file_changes(self, repo_with_history: Path) -> None:
        """Test iterating over all file changes."""
        scanner = GitHistoryScanner(repo_with_history)
        changes = list(scanner.iter_all_file_changes())

        # 3 commits with 1 file change each
        assert len(changes) == 3

        for commit, change in changes:
            assert isinstance(commit, CommitInfo)
            assert isinstance(change, FileChange)

    def test_get_commit_count(self, repo_with_history: Path) -> None:
        """Test getting commit count."""
        scanner = GitHistoryScanner(repo_with_history)
        count = scanner.get_commit_count()

        assert count == 3

    def test_filter_by_file_type(self, repo_with_history: Path) -> None:
        """Test filtering by file type."""
        scanner = GitHistoryScanner(
            repo_with_history,
            only_modifications_with_file_types=[".py"],
        )

        changes = list(scanner.iter_all_file_changes())

        assert len(changes) == 3
        assert all(c.path.endswith(".py") for _, c in changes)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_is_git_repository_true(self, tmp_path: Path) -> None:
        """Test is_git_repository returns True for git repo."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        assert is_git_repository(repo_path) is True

    def test_is_git_repository_false(self, tmp_path: Path) -> None:
        """Test is_git_repository returns False for non-git dir."""
        assert is_git_repository(tmp_path) is False

    def test_clone_repository(self, tmp_path: Path) -> None:
        """Test clone_repository helper with mock."""
        with patch.object(GitFetcher, "clone") as mock_clone:
            mock_clone.return_value = tmp_path / "repo"

            path, fetcher = clone_repository(
                "https://github.com/user/repo.git",
                target_dir=tmp_path,
                shallow=True,
            )

            assert path == tmp_path / "repo"
            assert isinstance(fetcher, GitFetcher)
            assert fetcher.shallow is True


class TestIntegration:
    """Integration tests for Git operations."""

    @pytest.fixture
    def full_repo(self, tmp_path: Path) -> Path:
        """Create a repository with various file types and changes."""
        repo_path = tmp_path / "full-repo"
        repo_path.mkdir()

        # Initialize
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create structure
        (repo_path / "src").mkdir()
        (repo_path / "src" / "main.py").write_text("API_KEY = 'sk-test123'")
        (repo_path / ".env").write_text("SECRET=abc123")

        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial with secrets"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Remove secret
        (repo_path / "src" / "main.py").write_text("API_KEY = os.getenv('API_KEY')")
        subprocess.run(
            ["git", "add", "."], cwd=repo_path, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Remove hardcoded secret"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        return repo_path

    def test_scan_repo_history(self, full_repo: Path) -> None:
        """Test scanning repository history for changes."""
        scanner = GitHistoryScanner(full_repo)

        found_secret = False
        for _commit, change in scanner.iter_all_file_changes():
            if change.content and "sk-test123" in change.content:
                found_secret = True
                break

        assert found_secret, "Should find secret in git history"

    def test_open_and_scan(self, full_repo: Path) -> None:
        """Test opening repo and scanning history."""
        with GitFetcher(url=str(full_repo)) as fetcher:
            fetcher.open_local(full_repo)
            head = fetcher.get_head_commit()

            scanner = GitHistoryScanner(full_repo)
            commits = list(scanner.iter_commits())

            assert len(head) == 40
            assert len(commits) == 2
