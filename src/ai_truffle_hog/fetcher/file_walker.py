"""File enumeration and filtering for scanning.

This module provides functionality for walking directory trees
and filtering files based on extension and path rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


# Default file extensions to scan for secrets
DEFAULT_INCLUDE_EXTENSIONS: frozenset[str] = frozenset(
    {
        # Configuration files
        ".env",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".xml",
        ".ini",
        ".cfg",
        ".conf",
        ".properties",
        # Programming languages
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".mjs",
        ".cjs",
        ".go",
        ".rb",
        ".php",
        ".java",
        ".kt",
        ".kts",
        ".scala",
        ".rs",
        ".swift",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".vb",
        ".fs",
        ".r",
        ".R",
        ".pl",
        ".pm",
        ".lua",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".psm1",
        # Web
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        # Data/Docs
        ".sql",
        ".md",
        ".txt",
        ".rst",
        ".csv",
        # Special files (no extension but important)
        "",  # Will handle files like Dockerfile, Makefile via name matching
    }
)

# Default path patterns to exclude (compiled regex)
DEFAULT_EXCLUDE_PATTERNS: tuple[str, ...] = (
    # Version control
    r"\.git(?:/|$)",
    r"\.svn(?:/|$)",
    r"\.hg(?:/|$)",
    # Dependencies
    r"node_modules(?:/|$)",
    r"vendor(?:/|$)",
    r"\.bundle(?:/|$)",
    r"packages(?:/|$)",
    # Python
    r"__pycache__(?:/|$)",
    r"\.pytest_cache(?:/|$)",
    r"\.mypy_cache(?:/|$)",
    r"\.ruff_cache(?:/|$)",
    r"\.tox(?:/|$)",
    r"\.nox(?:/|$)",
    r"venv(?:/|$)",
    r"\.venv(?:/|$)",
    r"\.eggs(?:/|$)",
    r".*\.egg-info(?:/|$)",
    # Build outputs
    r"dist(?:/|$)",
    r"build(?:/|$)",
    r"out(?:/|$)",
    r"target(?:/|$)",
    r"bin(?:/|$)",
    r"obj(?:/|$)",
    r"\.next(?:/|$)",
    r"\.nuxt(?:/|$)",
    # IDE
    r"\.idea(?:/|$)",
    r"\.vscode(?:/|$)",
    r"\.vs(?:/|$)",
    # OS
    r"\.DS_Store$",
    r"Thumbs\.db$",
    # Minified files
    r".*\.min\.js$",
    r".*\.min\.css$",
    # Compiled/Binary patterns
    r".*\.pyc$",
    r".*\.pyo$",
    r".*\.so$",
    r".*\.dylib$",
    r".*\.dll$",
    r".*\.exe$",
    r".*\.o$",
    r".*\.a$",
    r".*\.class$",
    r".*\.jar$",
    r".*\.war$",
    # Archives
    r".*\.zip$",
    r".*\.tar$",
    r".*\.gz$",
    r".*\.bz2$",
    r".*\.xz$",
    r".*\.rar$",
    r".*\.7z$",
    # Images
    r".*\.png$",
    r".*\.jpg$",
    r".*\.jpeg$",
    r".*\.gif$",
    r".*\.ico$",
    r".*\.svg$",
    r".*\.webp$",
    r".*\.bmp$",
    # Media
    r".*\.mp3$",
    r".*\.mp4$",
    r".*\.wav$",
    r".*\.avi$",
    r".*\.mov$",
    r".*\.webm$",
    r".*\.pdf$",
    r".*\.doc$",
    r".*\.docx$",
    r".*\.xls$",
    r".*\.xlsx$",
    r".*\.ppt$",
    r".*\.pptx$",
    # Fonts
    r".*\.ttf$",
    r".*\.otf$",
    r".*\.woff$",
    r".*\.woff2$",
    r".*\.eot$",
    # Lock files (often large, rarely contain secrets)
    r"package-lock\.json$",
    r"yarn\.lock$",
    r"pnpm-lock\.yaml$",
    r"Gemfile\.lock$",
    r"Cargo\.lock$",
    r"poetry\.lock$",
    r"composer\.lock$",
)

# Special filenames without extensions that should be scanned
SPECIAL_FILENAMES: frozenset[str] = frozenset(
    {
        "Dockerfile",
        "Makefile",
        "Rakefile",
        "Gemfile",
        "Procfile",
        "Vagrantfile",
        "Jenkinsfile",
        ".env",
        ".env.local",
        ".env.development",
        ".env.production",
        ".env.test",
        ".envrc",
        ".npmrc",
        ".yarnrc",
        ".babelrc",
        ".eslintrc",
        ".prettierrc",
        ".gitconfig",
        ".gitattributes",
        ".editorconfig",
        "docker-compose",
        "docker-compose.yml",
        "docker-compose.yaml",
    }
)


@dataclass
class FileFilter:
    """Configurable file filtering rules.

    Determines which files should be included or excluded from scanning
    based on extension, path patterns, size, and other criteria.

    Attributes:
        include_extensions: Set of file extensions to include (with dot prefix).
        exclude_patterns: List of compiled regex patterns for path exclusion.
        max_file_size_bytes: Maximum file size in bytes to scan.
        skip_hidden: Whether to skip hidden files/directories.
        skip_symlinks: Whether to skip symbolic links.
        special_filenames: Set of special filenames to always include.
    """

    include_extensions: frozenset[str] = field(
        default_factory=lambda: DEFAULT_INCLUDE_EXTENSIONS
    )
    exclude_patterns: tuple[re.Pattern[str], ...] = field(default_factory=tuple)
    max_file_size_bytes: int = 1024 * 1024  # 1 MB default
    skip_hidden: bool = True
    skip_symlinks: bool = True
    special_filenames: frozenset[str] = field(default_factory=lambda: SPECIAL_FILENAMES)

    def __post_init__(self) -> None:
        """Compile exclude patterns if provided as strings."""
        if not self.exclude_patterns:
            # Compile default patterns
            self.exclude_patterns = tuple(
                re.compile(pattern, re.IGNORECASE)
                for pattern in DEFAULT_EXCLUDE_PATTERNS
            )

    @classmethod
    def from_config(
        cls,
        include_extensions: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_file_size_kb: int = 1024,
        skip_hidden: bool = True,
        skip_symlinks: bool = True,
    ) -> FileFilter:
        """Create a FileFilter from configuration values.

        Args:
            include_extensions: List of extensions to include.
            exclude_patterns: List of regex patterns to exclude.
            max_file_size_kb: Maximum file size in KB.
            skip_hidden: Whether to skip hidden files.
            skip_symlinks: Whether to skip symlinks.

        Returns:
            Configured FileFilter instance.
        """
        extensions = (
            frozenset(include_extensions)
            if include_extensions
            else DEFAULT_INCLUDE_EXTENSIONS
        )

        patterns = tuple(
            re.compile(p, re.IGNORECASE)
            for p in (exclude_patterns or DEFAULT_EXCLUDE_PATTERNS)
        )

        return cls(
            include_extensions=extensions,
            exclude_patterns=patterns,
            max_file_size_bytes=max_file_size_kb * 1024,
            skip_hidden=skip_hidden,
            skip_symlinks=skip_symlinks,
        )

    def should_include_path(self, path: Path, root: Path) -> bool:
        """Check if a path should be included based on exclusion patterns.

        Args:
            path: The path to check.
            root: The root directory of the scan.

        Returns:
            True if the path should be included, False otherwise.
        """
        # Get relative path for pattern matching
        try:
            relative = path.relative_to(root)
            relative_str = str(relative)
        except ValueError:
            relative_str = str(path)

        # Check against exclusion patterns
        for pattern in self.exclude_patterns:
            if pattern.search(relative_str):
                return False

        return True

    def should_include_file(self, path: Path, root: Path) -> bool:
        """Check if a file should be included for scanning.

        Args:
            path: The file path to check.
            root: The root directory of the scan.

        Returns:
            True if the file should be scanned, False otherwise.
        """
        # Run exclusion checks first
        if not self._passes_basic_checks(path):
            return False

        if not self.should_include_path(path, root):
            return False

        if not self._passes_size_check(path):
            return False

        # Check if it's a special filename or has valid extension
        if path.name in self.special_filenames:
            return True

        return path.suffix.lower() in self.include_extensions

    def _passes_basic_checks(self, path: Path) -> bool:
        """Check basic file requirements (is file, not symlink, not hidden)."""
        if not path.is_file():
            return False
        if self.skip_symlinks and path.is_symlink():
            return False
        return not (
            self.skip_hidden
            and path.name.startswith(".")
            and path.name not in self.special_filenames
        )

    def _passes_size_check(self, path: Path) -> bool:
        """Check file size requirements."""
        try:
            size = path.stat().st_size
            return 0 < size <= self.max_file_size_bytes
        except OSError:
            return False

    def is_likely_binary(self, path: Path) -> bool:
        """Check if a file is likely binary by reading first bytes.

        Args:
            path: The file path to check.

        Returns:
            True if the file appears to be binary, False otherwise.
        """
        try:
            with path.open("rb") as f:
                chunk = f.read(8192)

            # Check for null bytes (strong indicator of binary)
            if b"\x00" in chunk:
                return True

            # Check for high ratio of non-printable characters
            if chunk:
                non_printable = sum(
                    1
                    for b in chunk
                    if b < 32 and b not in (9, 10, 13)  # tab, newline, carriage return
                )
                if non_printable / len(chunk) > 0.1:  # >10% non-printable
                    return True

        except OSError:
            return True  # If we can't read it, treat as binary

        return False


@dataclass
class FileInfo:
    """Information about a file to be scanned.

    Attributes:
        path: Absolute path to the file.
        relative_path: Path relative to scan root.
        size_bytes: File size in bytes.
        extension: File extension (with dot).
    """

    path: Path
    relative_path: Path
    size_bytes: int
    extension: str

    @classmethod
    def from_path(cls, path: Path, root: Path) -> FileInfo:
        """Create FileInfo from a path.

        Args:
            path: The file path.
            root: The root directory of the scan.

        Returns:
            FileInfo instance.
        """
        try:
            relative = path.relative_to(root)
        except ValueError:
            relative = path

        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        return cls(
            path=path.resolve(),
            relative_path=relative,
            size_bytes=size,
            extension=path.suffix.lower(),
        )


class FileWalker:
    """Directory traversal with filtering.

    Walks a directory tree and yields files matching the configured
    filter criteria. Uses generators for memory efficiency.

    Example:
        >>> walker = FileWalker(Path("/project"), FileFilter())
        >>> for file_info in walker.walk():
        ...     print(file_info.relative_path)
    """

    def __init__(
        self,
        root: Path,
        file_filter: FileFilter | None = None,
    ) -> None:
        """Initialize the FileWalker.

        Args:
            root: Root directory to walk.
            file_filter: Filter configuration. Uses defaults if not provided.
        """
        self.root = root.resolve()
        self.filter = file_filter or FileFilter()
        self._files_scanned = 0
        self._files_skipped = 0
        self._bytes_scanned = 0

    @property
    def files_scanned(self) -> int:
        """Number of files that passed filtering."""
        return self._files_scanned

    @property
    def files_skipped(self) -> int:
        """Number of files that were skipped."""
        return self._files_skipped

    @property
    def bytes_scanned(self) -> int:
        """Total bytes of files that passed filtering."""
        return self._bytes_scanned

    def walk(self) -> Iterator[FileInfo]:
        """Walk the directory tree and yield matching files.

        Yields:
            FileInfo for each file that passes the filter.

        Raises:
            FileNotFoundError: If root directory doesn't exist.
            NotADirectoryError: If root is not a directory.
        """
        if not self.root.exists():
            raise FileNotFoundError(f"Directory not found: {self.root}")

        if not self.root.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.root}")

        # Reset counters
        self._files_scanned = 0
        self._files_skipped = 0
        self._bytes_scanned = 0

        # Use rglob for recursive traversal
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            if self.filter.should_include_file(path, self.root):
                # Additional binary check for files without known extension
                if (
                    path.suffix.lower() not in self.filter.include_extensions
                    and self.filter.is_likely_binary(path)
                ):
                    self._files_skipped += 1
                    continue

                file_info = FileInfo.from_path(path, self.root)
                self._files_scanned += 1
                self._bytes_scanned += file_info.size_bytes
                yield file_info
            else:
                self._files_skipped += 1

    def walk_paths(self) -> Iterator[Path]:
        """Walk the directory tree and yield just the paths.

        Convenience method when only paths are needed.

        Yields:
            Path for each file that passes the filter.
        """
        for file_info in self.walk():
            yield file_info.path

    def read_file(self, path: Path) -> tuple[str, int]:
        """Read file content and return with line count.

        Args:
            path: Path to the file to read.

        Returns:
            Tuple of (content, line_count).

        Raises:
            OSError: If file cannot be read.
            UnicodeDecodeError: If file is not valid UTF-8.
        """
        # Try UTF-8 first, fall back to latin-1
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")

        line_count = content.count("\n") + (
            1 if content and not content.endswith("\n") else 0
        )
        return content, line_count

    def read_file_safe(self, path: Path) -> tuple[str | None, int, str | None]:
        """Read file content safely, returning error info if failed.

        Args:
            path: Path to the file to read.

        Returns:
            Tuple of (content, line_count, error_message).
            If successful, error_message is None.
            If failed, content is None and line_count is 0.
        """
        try:
            content, line_count = self.read_file(path)
            return content, line_count, None
        except OSError as e:
            return None, 0, f"IO error: {e}"
        except Exception as e:
            return None, 0, f"Error reading file: {e}"


def create_default_walker(root: Path) -> FileWalker:
    """Create a FileWalker with default settings.

    Args:
        root: Root directory to walk.

    Returns:
        Configured FileWalker instance.
    """
    return FileWalker(root, FileFilter())


def create_walker_from_config(
    root: Path,
    file_extensions: list[str] | None = None,
    skip_paths: list[str] | None = None,
    max_file_size_kb: int = 1024,
) -> FileWalker:
    """Create a FileWalker from configuration values.

    Args:
        root: Root directory to walk.
        file_extensions: List of extensions to include.
        skip_paths: List of path patterns to skip.
        max_file_size_kb: Maximum file size in KB.

    Returns:
        Configured FileWalker instance.
    """
    # Convert skip_paths to regex patterns
    exclude_patterns: list[str] | None = None
    if skip_paths:
        exclude_patterns = [rf"{re.escape(p)}(?:/|$)" for p in skip_paths]
        # Add default binary/archive patterns
        exclude_patterns.extend(
            [
                r".*\.pyc$",
                r".*\.so$",
                r".*\.dll$",
                r".*\.exe$",
                r".*\.zip$",
                r".*\.tar$",
                r".*\.gz$",
                r".*\.png$",
                r".*\.jpg$",
                r".*\.gif$",
            ]
        )

    file_filter = FileFilter.from_config(
        include_extensions=file_extensions,
        exclude_patterns=exclude_patterns,
        max_file_size_kb=max_file_size_kb,
    )

    return FileWalker(root, file_filter)
