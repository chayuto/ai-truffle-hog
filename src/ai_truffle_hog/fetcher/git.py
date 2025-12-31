"""Git repository operations.

This module provides functionality for cloning and managing
Git repositories during scanning, including history traversal
using PyDriller for memory-efficient commit analysis.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError
from pydriller import Repository as PyDrillerRepository

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime


@dataclass
class CommitInfo:
    """Information about a git commit.

    Attributes:
        hash: The full commit hash.
        short_hash: Abbreviated commit hash (first 8 chars).
        author: Author name.
        author_email: Author email.
        date: Commit timestamp.
        message: Commit message.
        is_merge: Whether this is a merge commit.
    """

    hash: str
    short_hash: str
    author: str
    author_email: str
    date: datetime
    message: str
    is_merge: bool = False

    @classmethod
    def from_pydriller_commit(cls, commit: Any) -> CommitInfo:
        """Create CommitInfo from a PyDriller commit object."""
        return cls(
            hash=commit.hash,
            short_hash=commit.hash[:8],
            author=commit.author.name or "Unknown",
            author_email=commit.author.email or "",
            date=commit.author_date,
            message=commit.msg.strip(),
            is_merge=commit.merge,
        )


@dataclass
class FileChange:
    """Information about a file change in a commit.

    Attributes:
        path: Path to the file.
        old_path: Previous path if renamed.
        content: File content after change (None if deleted).
        diff: The diff content.
        added_lines: Number of lines added.
        deleted_lines: Number of lines deleted.
        is_added: Whether the file was added.
        is_deleted: Whether the file was deleted.
        is_modified: Whether the file was modified.
        is_renamed: Whether the file was renamed.
    """

    path: str
    old_path: str | None
    content: str | None
    diff: str | None
    added_lines: int
    deleted_lines: int
    is_added: bool = False
    is_deleted: bool = False
    is_modified: bool = False
    is_renamed: bool = False

    @classmethod
    def from_pydriller_modification(cls, mod: Any) -> FileChange:
        """Create FileChange from a PyDriller modification object."""
        return cls(
            path=mod.new_path or mod.old_path or "",
            old_path=mod.old_path if mod.old_path != mod.new_path else None,
            content=mod.source_code,
            diff=mod.diff,
            added_lines=mod.added_lines,
            deleted_lines=mod.deleted_lines,
            is_added=mod.change_type.name == "ADD",
            is_deleted=mod.change_type.name == "DELETE",
            is_modified=mod.change_type.name == "MODIFY",
            is_renamed=mod.change_type.name == "RENAME",
        )


@dataclass
class GitFetcher:
    """Clone and manage git repositories.

    Provides functionality to clone repositories (HTTPS or SSH),
    manage temporary directories, and access repository metadata.

    Example:
        >>> with GitFetcher("https://github.com/user/repo") as fetcher:
        ...     repo_path = fetcher.clone()
        ...     print(f"Cloned to: {repo_path}")
        ...     # Auto-cleanup on exit

    Attributes:
        url: Repository URL (HTTPS or SSH).
        repo_path: Local path after cloning.
        shallow: Whether to do a shallow clone.
    """

    url: str
    repo_path: Path | None = field(default=None, init=False)
    shallow: bool = False
    _temp_dir: Path | None = field(default=None, init=False, repr=False)
    _repo: Repo | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate URL format."""
        self._validate_url()

    def _validate_url(self) -> None:
        """Validate that the URL looks like a git repository URL."""
        # SSH format: git@github.com:user/repo.git
        if self.url.startswith("git@"):
            return

        # HTTPS format
        parsed = urlparse(self.url)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return

        # Local path
        path = Path(self.url)
        if path.exists() and (path / ".git").exists():
            return

        raise ValueError(f"Invalid git repository URL or path: {self.url}")

    @property
    def repo_name(self) -> str:
        """Extract repository name from URL."""
        # Handle SSH format: git@github.com:user/repo.git
        if self.url.startswith("git@"):
            path_part = self.url.split(":")[-1]
            name = path_part.split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            return name

        # Handle HTTPS format
        parsed = urlparse(self.url)
        path = parsed.path.rstrip("/")
        name = path.split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name or "repo"

    def clone(self, target_dir: Path | None = None) -> Path:
        """Clone the repository to a local directory.

        Args:
            target_dir: Optional target directory. If not provided,
                       a temporary directory will be created.

        Returns:
            Path to the cloned repository.

        Raises:
            GitCommandError: If cloning fails.
        """
        if self.repo_path and self.repo_path.exists():
            return self.repo_path

        # Create target directory
        if target_dir:
            self.repo_path = target_dir / self.repo_name
            self.repo_path.mkdir(parents=True, exist_ok=True)
        else:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="aitruffle_"))
            self.repo_path = self._temp_dir / self.repo_name

        # Clone options
        clone_kwargs: dict[str, object] = {}
        if self.shallow:
            clone_kwargs["depth"] = 1

        try:
            self._repo = Repo.clone_from(
                self.url,
                str(self.repo_path),
                **clone_kwargs,
            )
        except GitCommandError as e:
            self.cleanup()
            raise GitCommandError(
                f"Failed to clone repository: {self.url}", e.status
            ) from e

        return self.repo_path

    def open_local(self, path: Path) -> Path:
        """Open an existing local repository.

        Args:
            path: Path to the local repository.

        Returns:
            The repository path.

        Raises:
            InvalidGitRepositoryError: If path is not a git repository.
        """
        path = path.resolve()
        if not (path / ".git").exists():
            raise InvalidGitRepositoryError(f"Not a git repository: {path}")

        self._repo = Repo(path)
        self.repo_path = path
        return self.repo_path

    def get_head_commit(self) -> str:
        """Get the HEAD commit hash.

        Returns:
            The full commit hash of HEAD.

        Raises:
            ValueError: If repository not cloned/opened.
        """
        if not self._repo:
            raise ValueError("Repository not cloned or opened")
        return str(self._repo.head.commit.hexsha)

    def get_branch(self) -> str:
        """Get the current branch name.

        Returns:
            Current branch name, or 'HEAD' if detached.
        """
        if not self._repo:
            raise ValueError("Repository not cloned or opened")

        try:
            return str(self._repo.active_branch.name)
        except TypeError:
            return "HEAD"

    def cleanup(self) -> None:
        """Clean up temporary directory if created."""
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None
            self.repo_path = None
            self._repo = None

    def __enter__(self) -> GitFetcher:
        """Context manager entry."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Context manager exit with cleanup."""
        self.cleanup()


class GitHistoryScanner:
    """Scan git history for file changes using PyDriller.

    Uses PyDriller for memory-efficient traversal of git history
    using generators. Suitable for large repositories.

    Example:
        >>> scanner = GitHistoryScanner(Path("/path/to/repo"))
        >>> for commit, changes in scanner.iter_commits_with_changes():
        ...     for change in changes:
        ...         print(f"{commit.short_hash}: {change.path}")
    """

    def __init__(
        self,
        repo_path: Path,
        since: datetime | None = None,
        to: datetime | None = None,
        only_in_branch: str | None = None,
        only_modifications_with_file_types: list[str] | None = None,
    ) -> None:
        """Initialize the history scanner.

        Args:
            repo_path: Path to the git repository.
            since: Only include commits after this date.
            to: Only include commits before this date.
            only_in_branch: Only include commits in this branch.
            only_modifications_with_file_types: Filter by file extensions.
        """
        self.repo_path = repo_path.resolve()
        self.since = since
        self.to = to
        self.only_in_branch = only_in_branch
        self.only_modifications_with_file_types = only_modifications_with_file_types

        if not (self.repo_path / ".git").exists():
            raise InvalidGitRepositoryError(f"Not a git repository: {self.repo_path}")

    def _get_pydriller_kwargs(self) -> dict[str, object]:
        """Build kwargs for PyDriller Repository."""
        kwargs: dict[str, object] = {
            "path_to_repo": str(self.repo_path),
        }

        if self.since:
            kwargs["since"] = self.since
        if self.to:
            kwargs["to"] = self.to
        if self.only_in_branch:
            kwargs["only_in_branch"] = self.only_in_branch
        if self.only_modifications_with_file_types:
            kwargs["only_modifications_with_file_types"] = (
                self.only_modifications_with_file_types
            )

        return kwargs

    def iter_commits(self) -> Iterator[CommitInfo]:
        """Iterate over commits in the repository.

        Yields:
            CommitInfo for each commit.
        """
        kwargs = self._get_pydriller_kwargs()
        for commit in PyDrillerRepository(**kwargs).traverse_commits():
            yield CommitInfo.from_pydriller_commit(commit)

    def iter_commits_with_changes(
        self,
    ) -> Iterator[tuple[CommitInfo, list[FileChange]]]:
        """Iterate over commits with their file changes.

        Yields:
            Tuple of (CommitInfo, list of FileChange) for each commit.
        """
        kwargs = self._get_pydriller_kwargs()
        for commit in PyDrillerRepository(**kwargs).traverse_commits():
            commit_info = CommitInfo.from_pydriller_commit(commit)
            changes = [
                FileChange.from_pydriller_modification(mod)
                for mod in commit.modified_files
            ]
            yield commit_info, changes

    def iter_all_file_changes(self) -> Iterator[tuple[CommitInfo, FileChange]]:
        """Iterate over all file changes across all commits.

        Yields:
            Tuple of (CommitInfo, FileChange) for each file change.
        """
        for commit_info, changes in self.iter_commits_with_changes():
            for change in changes:
                yield commit_info, change

    def get_commit_count(self) -> int:
        """Get the total number of commits.

        Note: This traverses all commits, which may be slow for large repos.

        Returns:
            Number of commits.
        """
        return sum(1 for _ in self.iter_commits())


def clone_repository(
    url: str,
    target_dir: Path | None = None,
    shallow: bool = False,
) -> tuple[Path, GitFetcher]:
    """Clone a repository and return path with fetcher for cleanup.

    Convenience function for simple cloning operations.

    Args:
        url: Repository URL.
        target_dir: Optional target directory.
        shallow: Whether to do shallow clone.

    Returns:
        Tuple of (repo_path, GitFetcher).
        Caller is responsible for calling fetcher.cleanup().
    """
    fetcher = GitFetcher(url=url, shallow=shallow)
    repo_path = fetcher.clone(target_dir)
    return repo_path, fetcher


def is_git_repository(path: Path) -> bool:
    """Check if a path is a git repository.

    Args:
        path: Path to check.

    Returns:
        True if path is a git repository.
    """
    return (path / ".git").exists() or (path / ".git").is_file()
