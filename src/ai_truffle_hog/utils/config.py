"""Configuration management for AI Truffle Hog.

This module provides configuration loading and management using
Pydantic Settings with support for environment variables and TOML files.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScannerSettings(BaseSettings):
    """Scanner configuration settings."""

    model_config = SettingsConfigDict(env_prefix="ATH_SCANNER_")

    file_extensions: list[str] = Field(
        default=[
            ".py",
            ".js",
            ".ts",
            ".env",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".xml",
            ".properties",
            ".conf",
            ".go",
            ".rb",
            ".php",
        ],
        description="File extensions to scan",
    )
    max_file_size_kb: int = Field(
        default=1024,
        ge=1,
        description="Maximum file size in KB to scan",
    )
    skip_paths: list[str] = Field(
        default=[
            "node_modules",
            ".git",
            "__pycache__",
            "venv",
            ".venv",
            "dist",
            "build",
        ],
        description="Paths to skip during scanning",
    )
    entropy_threshold: float = Field(
        default=4.5,
        ge=0.0,
        le=8.0,
        description="Minimum entropy threshold for detection",
    )


class ValidatorSettings(BaseSettings):
    """Validator configuration settings."""

    model_config = SettingsConfigDict(env_prefix="ATH_VALIDATOR_")

    enabled: bool = Field(default=True, description="Enable key validation")
    timeout_seconds: int = Field(
        default=10,
        ge=1,
        description="HTTP request timeout in seconds",
    )
    max_concurrent: int = Field(
        default=5,
        ge=1,
        description="Maximum concurrent validation requests",
    )
    retry_count: int = Field(
        default=3,
        ge=0,
        description="Number of retries for failed requests",
    )
    retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.0,
        description="Delay between retries in seconds",
    )


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    model_config = SettingsConfigDict(env_prefix="ATH_LOGGING_")

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="json",
        description="Log format: 'json' or 'console'",
    )
    file: str | None = Field(default=None, description="Log file path")
    redact_secrets: bool = Field(
        default=True,
        description="Redact secrets in log output",
    )


class OutputSettings(BaseSettings):
    """Output configuration settings."""

    model_config = SettingsConfigDict(env_prefix="ATH_OUTPUT_")

    format: str = Field(
        default="table",
        description="Output format: 'table' or 'json'",
    )
    show_context: bool = Field(
        default=True,
        description="Show context around findings",
    )
    context_lines: int = Field(
        default=3,
        ge=0,
        description="Number of context lines to show",
    )


class Settings(BaseSettings):
    """Main application settings container."""

    model_config = SettingsConfigDict(
        env_prefix="ATH_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    scanner: ScannerSettings = Field(default_factory=ScannerSettings)
    validator: ValidatorSettings = Field(default_factory=ValidatorSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    output: OutputSettings = Field(default_factory=OutputSettings)


def load_config(config_path: Path | None = None) -> Settings:
    """Load configuration from file and environment.

    Priority (highest to lowest):
    1. Environment variables
    2. Config file
    3. Defaults

    Args:
        config_path: Optional path to a TOML configuration file.

    Returns:
        Loaded Settings instance.
    """
    config_data: dict[str, object] = {}

    if config_path and config_path.exists():
        import tomllib

        with config_path.open("rb") as f:
            config_data = tomllib.load(f)

    return Settings(**config_data)  # type: ignore[arg-type]


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance.

    Initializes settings on first access.

    Returns:
        The global Settings instance.
    """
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance.

    Useful for testing.
    """
    global _settings
    _settings = None
