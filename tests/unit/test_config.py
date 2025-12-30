"""Unit tests for configuration management."""

import tempfile
from pathlib import Path

from ai_truffle_hog.utils.config import (
    LoggingSettings,
    OutputSettings,
    ScannerSettings,
    Settings,
    ValidatorSettings,
    get_settings,
    load_config,
    reset_settings,
)


class TestScannerSettings:
    """Tests for ScannerSettings."""

    def test_defaults(self) -> None:
        """Default values are set."""
        settings = ScannerSettings()
        assert ".py" in settings.file_extensions
        assert ".git" in settings.skip_paths
        assert settings.max_file_size_kb == 1024
        assert settings.entropy_threshold == 4.5

    def test_custom_values(self) -> None:
        """Custom values are accepted."""
        settings = ScannerSettings(
            file_extensions=[".txt"],
            max_file_size_kb=512,
            entropy_threshold=3.5,
        )
        assert settings.file_extensions == [".txt"]
        assert settings.max_file_size_kb == 512
        assert settings.entropy_threshold == 3.5


class TestValidatorSettings:
    """Tests for ValidatorSettings."""

    def test_defaults(self) -> None:
        """Default values are set."""
        settings = ValidatorSettings()
        assert settings.enabled is True
        assert settings.timeout_seconds == 10
        assert settings.max_concurrent == 5
        assert settings.retry_count == 3

    def test_disabled(self) -> None:
        """Validation can be disabled."""
        settings = ValidatorSettings(enabled=False)
        assert settings.enabled is False


class TestLoggingSettings:
    """Tests for LoggingSettings."""

    def test_defaults(self) -> None:
        """Default values are set."""
        settings = LoggingSettings()
        assert settings.level == "INFO"
        assert settings.format == "json"
        assert settings.file is None
        assert settings.redact_secrets is True


class TestOutputSettings:
    """Tests for OutputSettings."""

    def test_defaults(self) -> None:
        """Default values are set."""
        settings = OutputSettings()
        assert settings.format == "table"
        assert settings.show_context is True
        assert settings.context_lines == 3


class TestSettings:
    """Tests for main Settings container."""

    def test_defaults(self) -> None:
        """Nested settings have defaults."""
        settings = Settings()
        assert isinstance(settings.scanner, ScannerSettings)
        assert isinstance(settings.validator, ValidatorSettings)
        assert isinstance(settings.logging, LoggingSettings)
        assert isinstance(settings.output, OutputSettings)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_defaults(self) -> None:
        """Load config without file uses defaults."""
        config = load_config()
        assert isinstance(config, Settings)

    def test_load_from_toml(self) -> None:
        """Load config from TOML file."""
        toml_content = """
[scanner]
max_file_size_kb = 512
entropy_threshold = 4.0

[validator]
enabled = false
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()
            config = load_config(Path(f.name))

        assert config.scanner.max_file_size_kb == 512
        assert config.scanner.entropy_threshold == 4.0
        assert config.validator.enabled is False


class TestGetSettings:
    """Tests for get_settings singleton."""

    def test_returns_settings(self) -> None:
        """get_settings returns Settings instance."""
        reset_settings()  # Ensure clean state
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_singleton_pattern(self) -> None:
        """get_settings returns same instance."""
        reset_settings()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_reset_settings(self) -> None:
        """reset_settings clears the singleton."""
        settings1 = get_settings()
        reset_settings()
        settings2 = get_settings()
        # New instance after reset
        assert settings1 is not settings2
