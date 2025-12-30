"""Core data models for AI Truffle Hog.

This module defines the Pydantic models used throughout the application
for representing secrets, scan results, and validation states.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Status of key validation."""

    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    SKIPPED = "skipped"


class SecretCandidate(BaseModel):
    """A potential secret found during scanning.

    Represents a single detected API key or secret with its location,
    context, and validation status.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for this finding")
    provider: str = Field(..., description="Provider name (e.g., 'openai', 'anthropic')")
    secret_value: str = Field(..., description="The actual secret value")
    file_path: str = Field(..., description="Path to the file containing the secret")
    line_number: int = Field(..., ge=1, description="Line number where secret was found")
    column_start: int = Field(default=0, ge=0, description="Starting column position")
    column_end: int = Field(default=0, ge=0, description="Ending column position")
    context_before: str = Field(default="", description="Lines before the secret")
    context_after: str = Field(default="", description="Lines after the secret")
    variable_name: Optional[str] = Field(default=None, description="Variable name if detected")
    pattern_name: str = Field(default="", description="Name of the pattern that matched")
    entropy_score: float = Field(default=0.0, ge=0.0, description="Shannon entropy of the secret")
    validation_status: ValidationStatus = Field(
        default=ValidationStatus.PENDING,
        description="Current validation status",
    )
    validation_timestamp: Optional[datetime] = Field(
        default=None,
        description="When validation was performed",
    )
    validation_message: Optional[str] = Field(
        default=None,
        description="Message from validation attempt",
    )
    validation_metadata: Optional[dict[str, str]] = Field(
        default=None,
        description="Additional metadata from validation",
    )


class ScanResult(BaseModel):
    """Result of scanning a single repository.

    Contains all findings from scanning one repository along with
    metadata about the scan process.
    """

    repo_url: str = Field(..., description="URL of the scanned repository")
    repo_path: Optional[str] = Field(default=None, description="Local path where repo was cloned")
    commit_hash: Optional[str] = Field(default=None, description="HEAD commit hash at scan time")
    scan_started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the scan started",
    )
    scan_completed_at: Optional[datetime] = Field(
        default=None,
        description="When the scan completed",
    )
    files_scanned: int = Field(default=0, ge=0, description="Number of files scanned")
    secrets_found: list[SecretCandidate] = Field(
        default_factory=list,
        description="List of secrets found",
    )
    errors: list[str] = Field(default_factory=list, description="Errors encountered during scan")

    @property
    def duration_seconds(self) -> float:
        """Calculate scan duration in seconds."""
        if self.scan_completed_at and self.scan_started_at:
            return (self.scan_completed_at - self.scan_started_at).total_seconds()
        return 0.0

    @property
    def secrets_count(self) -> int:
        """Get count of secrets found."""
        return len(self.secrets_found)


class ScanSession(BaseModel):
    """A complete scanning session.

    May include multiple repositories when scanning from a file.
    """

    session_id: UUID = Field(default_factory=uuid4, description="Unique session identifier")
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the session started",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When the session completed",
    )
    targets: list[str] = Field(default_factory=list, description="List of scan targets")
    results: list[ScanResult] = Field(default_factory=list, description="Results for each target")
    validate_keys: bool = Field(default=False, description="Whether key validation was enabled")

    @property
    def total_secrets_found(self) -> int:
        """Get total count of secrets found across all results."""
        return sum(len(r.secrets_found) for r in self.results)

    @property
    def total_files_scanned(self) -> int:
        """Get total count of files scanned across all results."""
        return sum(r.files_scanned for r in self.results)

    @property
    def duration_seconds(self) -> float:
        """Calculate total session duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
