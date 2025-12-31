"""Fetcher module for Git operations and file handling."""

from ai_truffle_hog.fetcher.file_walker import (
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_INCLUDE_EXTENSIONS,
    SPECIAL_FILENAMES,
    FileFilter,
    FileInfo,
    FileWalker,
    create_default_walker,
    create_walker_from_config,
)
from ai_truffle_hog.fetcher.git import (
    CommitInfo,
    FileChange,
    GitFetcher,
    GitHistoryScanner,
    clone_repository,
    is_git_repository,
)

__all__ = [
    "DEFAULT_EXCLUDE_PATTERNS",
    "DEFAULT_INCLUDE_EXTENSIONS",
    "SPECIAL_FILENAMES",
    "CommitInfo",
    "FileChange",
    "FileFilter",
    "FileInfo",
    "FileWalker",
    "GitFetcher",
    "GitHistoryScanner",
    "clone_repository",
    "create_default_walker",
    "create_walker_from_config",
    "is_git_repository",
]
