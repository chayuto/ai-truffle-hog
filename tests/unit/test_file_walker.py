"""Unit tests for FileWalker module."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

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


class TestDefaultConstants:
    """Tests for default constants."""

    def test_default_extensions_includes_common_config(self) -> None:
        """Test that common config file extensions are included."""
        assert ".env" in DEFAULT_INCLUDE_EXTENSIONS
        assert ".json" in DEFAULT_INCLUDE_EXTENSIONS
        assert ".yaml" in DEFAULT_INCLUDE_EXTENSIONS
        assert ".yml" in DEFAULT_INCLUDE_EXTENSIONS
        assert ".toml" in DEFAULT_INCLUDE_EXTENSIONS

    def test_default_extensions_includes_programming_languages(self) -> None:
        """Test that common programming language extensions are included."""
        assert ".py" in DEFAULT_INCLUDE_EXTENSIONS
        assert ".js" in DEFAULT_INCLUDE_EXTENSIONS
        assert ".ts" in DEFAULT_INCLUDE_EXTENSIONS
        assert ".go" in DEFAULT_INCLUDE_EXTENSIONS
        assert ".rb" in DEFAULT_INCLUDE_EXTENSIONS

    def test_default_exclude_patterns_has_git(self) -> None:
        """Test that .git directory is excluded by default."""
        patterns = [re.compile(p, re.IGNORECASE) for p in DEFAULT_EXCLUDE_PATTERNS]
        git_matched = any(p.search(".git/config") for p in patterns)
        assert git_matched

    def test_default_exclude_patterns_has_node_modules(self) -> None:
        """Test that node_modules is excluded by default."""
        patterns = [re.compile(p, re.IGNORECASE) for p in DEFAULT_EXCLUDE_PATTERNS]
        node_matched = any(p.search("node_modules/package.json") for p in patterns)
        assert node_matched

    def test_special_filenames_includes_dockerfile(self) -> None:
        """Test that Dockerfile is in special filenames."""
        assert "Dockerfile" in SPECIAL_FILENAMES

    def test_special_filenames_includes_env_variants(self) -> None:
        """Test that .env variants are in special filenames."""
        assert ".env" in SPECIAL_FILENAMES
        assert ".env.local" in SPECIAL_FILENAMES
        assert ".env.production" in SPECIAL_FILENAMES


class TestFileFilter:
    """Tests for FileFilter class."""

    def test_default_filter_creation(self) -> None:
        """Test creating a FileFilter with defaults."""
        file_filter = FileFilter()
        assert file_filter.max_file_size_bytes == 1024 * 1024
        assert file_filter.skip_hidden is True
        assert file_filter.skip_symlinks is True

    def test_from_config_custom_extensions(self) -> None:
        """Test creating FileFilter with custom extensions."""
        file_filter = FileFilter.from_config(
            include_extensions=[".py", ".txt"],
            max_file_size_kb=512,
        )
        assert ".py" in file_filter.include_extensions
        assert ".txt" in file_filter.include_extensions
        assert file_filter.max_file_size_bytes == 512 * 1024

    def test_from_config_custom_exclude_patterns(self) -> None:
        """Test creating FileFilter with custom exclude patterns."""
        file_filter = FileFilter.from_config(
            exclude_patterns=[r"test_.*\.py$", r"\.backup$"],
        )
        assert len(file_filter.exclude_patterns) == 2

    def test_should_include_path_excludes_git(self, tmp_path: Path) -> None:
        """Test that .git directory is excluded."""
        file_filter = FileFilter()
        git_file = tmp_path / ".git" / "config"
        assert file_filter.should_include_path(git_file, tmp_path) is False

    def test_should_include_path_excludes_node_modules(self, tmp_path: Path) -> None:
        """Test that node_modules directory is excluded."""
        file_filter = FileFilter()
        node_file = tmp_path / "node_modules" / "package" / "index.js"
        assert file_filter.should_include_path(node_file, tmp_path) is False

    def test_should_include_path_allows_normal_files(self, tmp_path: Path) -> None:
        """Test that normal source files are allowed."""
        file_filter = FileFilter()
        src_file = tmp_path / "src" / "main.py"
        assert file_filter.should_include_path(src_file, tmp_path) is True

    def test_should_include_file_basic(self, tmp_path: Path) -> None:
        """Test basic file inclusion check."""
        file_filter = FileFilter()

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        assert file_filter.should_include_file(test_file, tmp_path) is True

    def test_should_include_file_skips_empty(self, tmp_path: Path) -> None:
        """Test that empty files are skipped."""
        file_filter = FileFilter()

        empty_file = tmp_path / "empty.py"
        empty_file.touch()

        assert file_filter.should_include_file(empty_file, tmp_path) is False

    def test_should_include_file_skips_large_files(self, tmp_path: Path) -> None:
        """Test that files exceeding size limit are skipped."""
        file_filter = FileFilter.from_config(max_file_size_kb=1)  # 1 KB limit

        large_file = tmp_path / "large.py"
        large_file.write_text("x" * 2000)  # 2 KB

        assert file_filter.should_include_file(large_file, tmp_path) is False

    def test_should_include_file_skips_hidden(self, tmp_path: Path) -> None:
        """Test that hidden files are skipped by default."""
        file_filter = FileFilter()

        hidden_file = tmp_path / ".hidden.py"
        hidden_file.write_text("secret")

        assert file_filter.should_include_file(hidden_file, tmp_path) is False

    def test_should_include_file_allows_special_dotfiles(self, tmp_path: Path) -> None:
        """Test that special dotfiles like .env are allowed."""
        file_filter = FileFilter()

        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value")

        assert file_filter.should_include_file(env_file, tmp_path) is True

    def test_should_include_file_checks_extension(self, tmp_path: Path) -> None:
        """Test that only allowed extensions are included."""
        file_filter = FileFilter.from_config(include_extensions=[".py"])

        py_file = tmp_path / "main.py"
        py_file.write_text("code")

        jpg_file = tmp_path / "image.jpg"
        jpg_file.write_text("not really an image")

        assert file_filter.should_include_file(py_file, tmp_path) is True
        assert file_filter.should_include_file(jpg_file, tmp_path) is False

    def test_is_likely_binary_text_file(self, tmp_path: Path) -> None:
        """Test that text files are not marked as binary."""
        file_filter = FileFilter()

        text_file = tmp_path / "readme.txt"
        text_file.write_text("This is a text file\nwith multiple lines.")

        assert file_filter.is_likely_binary(text_file) is False

    def test_is_likely_binary_with_null_bytes(self, tmp_path: Path) -> None:
        """Test that files with null bytes are marked as binary."""
        file_filter = FileFilter()

        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"hello\x00world")

        assert file_filter.is_likely_binary(binary_file) is True


class TestFileInfo:
    """Tests for FileInfo class."""

    def test_from_path_basic(self, tmp_path: Path) -> None:
        """Test creating FileInfo from path."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('test')")

        info = FileInfo.from_path(test_file, tmp_path)

        assert info.path == test_file.resolve()
        assert info.relative_path == Path("test.py")
        assert info.size_bytes > 0
        assert info.extension == ".py"

    def test_from_path_nested(self, tmp_path: Path) -> None:
        """Test creating FileInfo from nested path."""
        nested_dir = tmp_path / "src" / "utils"
        nested_dir.mkdir(parents=True)

        test_file = nested_dir / "helper.py"
        test_file.write_text("def helper(): pass")

        info = FileInfo.from_path(test_file, tmp_path)

        assert info.relative_path == Path("src/utils/helper.py")

    def test_from_path_no_extension(self, tmp_path: Path) -> None:
        """Test creating FileInfo from file without extension."""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.11")

        info = FileInfo.from_path(dockerfile, tmp_path)

        assert info.extension == ""


class TestFileWalker:
    """Tests for FileWalker class."""

    def test_init_with_defaults(self, tmp_path: Path) -> None:
        """Test FileWalker initialization with defaults."""
        walker = FileWalker(tmp_path)
        assert walker.root == tmp_path.resolve()
        assert isinstance(walker.filter, FileFilter)

    def test_init_with_custom_filter(self, tmp_path: Path) -> None:
        """Test FileWalker initialization with custom filter."""
        custom_filter = FileFilter.from_config(include_extensions=[".txt"])
        walker = FileWalker(tmp_path, custom_filter)
        assert walker.filter == custom_filter

    def test_walk_empty_directory(self, tmp_path: Path) -> None:
        """Test walking an empty directory."""
        walker = FileWalker(tmp_path)
        files = list(walker.walk())
        assert len(files) == 0

    def test_walk_single_file(self, tmp_path: Path) -> None:
        """Test walking a directory with one file."""
        test_file = tmp_path / "main.py"
        test_file.write_text("print('hello')")

        walker = FileWalker(tmp_path)
        files = list(walker.walk())

        assert len(files) == 1
        assert files[0].relative_path == Path("main.py")

    def test_walk_multiple_files(self, tmp_path: Path) -> None:
        """Test walking a directory with multiple files."""
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")
        (tmp_path / "c.js").write_text("c")

        walker = FileWalker(tmp_path)
        files = list(walker.walk())

        assert len(files) == 3

    def test_walk_nested_directories(self, tmp_path: Path) -> None:
        """Test walking nested directory structure."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "utils").mkdir()

        (tmp_path / "main.py").write_text("main")
        (tmp_path / "src" / "app.py").write_text("app")
        (tmp_path / "src" / "utils" / "helper.py").write_text("helper")

        walker = FileWalker(tmp_path)
        files = list(walker.walk())

        assert len(files) == 3
        paths = {str(f.relative_path) for f in files}
        assert "main.py" in paths
        assert "src/app.py" in paths or "src\\app.py" in paths

    def test_walk_excludes_git_directory(self, tmp_path: Path) -> None:
        """Test that .git directory is excluded."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        (tmp_path / "main.py").write_text("main")
        (git_dir / "config").write_text("git config")

        walker = FileWalker(tmp_path)
        files = list(walker.walk())

        assert len(files) == 1
        assert files[0].relative_path == Path("main.py")

    def test_walk_excludes_node_modules(self, tmp_path: Path) -> None:
        """Test that node_modules directory is excluded."""
        node_dir = tmp_path / "node_modules" / "lodash"
        node_dir.mkdir(parents=True)

        (tmp_path / "index.js").write_text("main")
        (node_dir / "index.js").write_text("lodash")

        walker = FileWalker(tmp_path)
        files = list(walker.walk())

        assert len(files) == 1
        assert files[0].relative_path == Path("index.js")

    def test_walk_includes_special_files(self, tmp_path: Path) -> None:
        """Test that special files like Dockerfile are included."""
        (tmp_path / "Dockerfile").write_text("FROM python:3.11")
        (tmp_path / ".env").write_text("KEY=value")

        walker = FileWalker(tmp_path)
        files = list(walker.walk())

        names = {f.relative_path.name for f in files}
        assert "Dockerfile" in names
        assert ".env" in names

    def test_walk_counters(self, tmp_path: Path) -> None:
        """Test that file counters are updated correctly."""
        (tmp_path / "included.py").write_text("code")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git")

        walker = FileWalker(tmp_path)
        _ = list(walker.walk())

        assert walker.files_scanned == 1
        assert walker.files_skipped >= 1
        assert walker.bytes_scanned > 0

    def test_walk_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test walking a nonexistent directory raises error."""
        nonexistent = tmp_path / "nonexistent"
        walker = FileWalker(nonexistent)

        with pytest.raises(FileNotFoundError):
            list(walker.walk())

    def test_walk_file_instead_of_directory(self, tmp_path: Path) -> None:
        """Test walking a file instead of directory raises error."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        walker = FileWalker(file_path)

        with pytest.raises(NotADirectoryError):
            list(walker.walk())

    def test_walk_paths(self, tmp_path: Path) -> None:
        """Test walk_paths yields Path objects."""
        (tmp_path / "main.py").write_text("code")

        walker = FileWalker(tmp_path)
        paths = list(walker.walk_paths())

        assert len(paths) == 1
        assert isinstance(paths[0], Path)

    def test_read_file_utf8(self, tmp_path: Path) -> None:
        """Test reading UTF-8 file."""
        test_file = tmp_path / "test.py"
        content = "print('hello')\n# Comment"
        test_file.write_text(content)

        walker = FileWalker(tmp_path)
        read_content, line_count = walker.read_file(test_file)

        assert read_content == content
        assert line_count == 2

    def test_read_file_single_line(self, tmp_path: Path) -> None:
        """Test reading file with single line (no newline)."""
        test_file = tmp_path / "test.py"
        test_file.write_text("single line")

        walker = FileWalker(tmp_path)
        _, line_count = walker.read_file(test_file)

        assert line_count == 1

    def test_read_file_safe_success(self, tmp_path: Path) -> None:
        """Test read_file_safe with valid file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        walker = FileWalker(tmp_path)
        content, line_count, error = walker.read_file_safe(test_file)

        assert content == "content"
        assert line_count == 1
        assert error is None

    def test_read_file_safe_nonexistent(self, tmp_path: Path) -> None:
        """Test read_file_safe with nonexistent file."""
        walker = FileWalker(tmp_path)
        content, line_count, error = walker.read_file_safe(tmp_path / "missing.py")

        assert content is None
        assert line_count == 0
        assert error is not None


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_default_walker(self, tmp_path: Path) -> None:
        """Test create_default_walker function."""
        walker = create_default_walker(tmp_path)
        assert isinstance(walker, FileWalker)
        assert walker.root == tmp_path.resolve()

    def test_create_walker_from_config(self, tmp_path: Path) -> None:
        """Test create_walker_from_config function."""
        walker = create_walker_from_config(
            tmp_path,
            file_extensions=[".py", ".js"],
            skip_paths=["build", "dist"],
            max_file_size_kb=512,
        )

        assert isinstance(walker, FileWalker)
        assert ".py" in walker.filter.include_extensions
        assert walker.filter.max_file_size_bytes == 512 * 1024

    def test_create_walker_from_config_defaults(self, tmp_path: Path) -> None:
        """Test create_walker_from_config with defaults."""
        walker = create_walker_from_config(tmp_path)
        assert isinstance(walker, FileWalker)


class TestIntegration:
    """Integration tests for FileWalker."""

    def test_scan_realistic_project_structure(self, tmp_path: Path) -> None:
        """Test scanning a realistic project structure."""
        # Create project structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        node_modules = tmp_path / "node_modules" / "pkg"
        node_modules.mkdir(parents=True)

        # Create files
        (tmp_path / "README.md").write_text("# Project")
        (tmp_path / ".env").write_text("API_KEY=secret")
        (tmp_path / "Dockerfile").write_text("FROM python:3.11")
        (src_dir / "main.py").write_text("def main(): pass")
        (src_dir / "utils.py").write_text("def util(): pass")
        (tests_dir / "test_main.py").write_text("def test(): pass")
        (git_dir / "config").write_text("git config")
        (node_modules / "index.js").write_text("module.exports = {}")

        walker = FileWalker(tmp_path)
        files = list(walker.walk())

        # Should include: README.md, .env, Dockerfile, main.py, utils.py, test_main.py
        # Should exclude: .git/config, node_modules/pkg/index.js
        file_names = {f.relative_path.name for f in files}

        assert "README.md" in file_names
        assert ".env" in file_names
        assert "Dockerfile" in file_names
        assert "main.py" in file_names
        assert "utils.py" in file_names
        assert "test_main.py" in file_names
        assert "config" not in file_names
        assert len(files) == 6
