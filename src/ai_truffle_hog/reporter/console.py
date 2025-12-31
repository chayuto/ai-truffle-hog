"""Console output reporter using Rich.

This module provides rich console output functionality for
displaying scan results in a formatted table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from ai_truffle_hog.core.scanner import ScanMatch


@dataclass
class ConsoleSummary:
    """Summary statistics for console output.

    Attributes:
        total_files: Number of files scanned.
        total_matches: Total number of matches found.
        matches_by_provider: Count of matches per provider.
        validated_count: Number of matches validated.
        valid_count: Number of confirmed valid keys.
    """

    total_files: int = 0
    total_matches: int = 0
    matches_by_provider: dict[str, int] = field(default_factory=dict)
    validated_count: int = 0
    valid_count: int = 0

    def add_match(self, provider: str) -> None:
        """Add a match for a provider."""
        self.total_matches += 1
        self.matches_by_provider[provider] = (
            self.matches_by_provider.get(provider, 0) + 1
        )


class ConsoleReporter:
    """Rich console reporter for scan results.

    Provides colorful, formatted output for terminal display including:
    - Tables of findings
    - Color-coded severity
    - Summary statistics
    - Progress indicators

    Example:
        ```python
        reporter = ConsoleReporter()
        reporter.print_matches(matches)
        reporter.print_summary(summary)
        ```
    """

    # Provider color mappings for severity
    SEVERITY_COLORS: ClassVar[dict[str, str]] = {
        "openai": "red",
        "anthropic": "red",
        "huggingface": "yellow",
        "cohere": "yellow",
        "replicate": "yellow",
        "google_gemini": "red",
        "groq": "yellow",
        "langsmith": "yellow",
    }

    # Status colors
    STATUS_COLORS: ClassVar[dict[str, str]] = {
        "valid": "red",
        "invalid": "green",
        "error": "yellow",
        "skipped": "dim",
        "unknown": "white",
    }

    def __init__(
        self,
        console: Console | None = None,
        verbose: bool = False,
        show_context: bool = True,
    ) -> None:
        """Initialize the console reporter.

        Args:
            console: Rich Console instance (creates one if None).
            verbose: Whether to show verbose output.
            show_context: Whether to show context lines.
        """
        self.console = console or Console()
        self.verbose = verbose
        self.show_context = show_context

    def _get_severity_color(self, provider: str) -> str:
        """Get color for provider severity."""
        return self.SEVERITY_COLORS.get(provider, "white")

    def print_header(self, title: str = "AI Truffle Hog Scan Results") -> None:
        """Print a styled header.

        Args:
            title: Title text to display.
        """
        self.console.print()
        self.console.print(
            Panel(
                f"[bold blue]{title}[/bold blue]",
                border_style="blue",
            )
        )
        self.console.print()

    def print_matches(self, matches: list[ScanMatch]) -> None:
        """Print matches in a formatted table.

        Args:
            matches: List of scan matches to display.
        """
        if not matches:
            self.console.print("[dim]No secrets found.[/dim]")
            return

        table = Table(
            title="Detected Secrets",
            show_header=True,
            header_style="bold magenta",
            border_style="bright_blue",
        )

        table.add_column("Provider", style="cyan", no_wrap=True)
        table.add_column("File", style="green")
        table.add_column("Line", justify="right", style="yellow")
        table.add_column("Secret", style="red")
        table.add_column("Entropy", justify="right", style="blue")

        for match in matches:
            color = self._get_severity_color(match.provider)
            provider_text = Text(match.provider.upper(), style=f"bold {color}")

            # Truncate file path if too long
            file_path = match.file_path
            if len(file_path) > 40:
                file_path = "..." + file_path[-37:]

            table.add_row(
                provider_text,
                file_path,
                str(match.line_number),
                match.redacted_value,
                f"{match.entropy:.2f}" if match.entropy else "-",
            )

        self.console.print(table)

    def print_match_detail(self, match: ScanMatch) -> None:
        """Print detailed information for a single match.

        Args:
            match: The match to display in detail.
        """
        color = self._get_severity_color(match.provider)

        self.console.print()
        self.console.print(
            f"[bold {color}]● {match.provider.upper()}[/bold {color}] "
            f"[dim]in[/dim] [green]{match.file_path}[/green]"
            f"[dim]:[/dim][yellow]{match.line_number}[/yellow]"
        )

        # Show context if available
        if self.show_context:
            if match.context_before:
                for line in match.context_before:
                    self.console.print(f"  [dim]{line}[/dim]")

            # Highlight the secret line
            self.console.print(f"  [bold red]{match.line_content}[/bold red]")

            if match.context_after:
                for line in match.context_after:
                    self.console.print(f"  [dim]{line}[/dim]")

    def print_summary(self, summary: ConsoleSummary) -> None:
        """Print summary statistics.

        Args:
            summary: Summary statistics to display.
        """
        self.console.print()

        if summary.total_matches == 0:
            self.console.print(
                Panel(
                    "[green]✓ No secrets detected[/green]",
                    title="Scan Complete",
                    border_style="green",
                )
            )
            return

        # Create summary table
        table = Table(
            title="Scan Summary",
            show_header=True,
            header_style="bold",
            border_style="yellow",
        )

        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="yellow")

        table.add_row("Total Files Scanned", str(summary.total_files))
        table.add_row(
            "Total Secrets Found",
            Text(str(summary.total_matches), style="bold red"),
        )

        if summary.validated_count > 0:
            table.add_row("Validated", str(summary.validated_count))
            table.add_row(
                "Confirmed Valid",
                Text(str(summary.valid_count), style="bold red"),
            )

        self.console.print(table)

        # Show by provider breakdown
        if summary.matches_by_provider:
            self.console.print()
            provider_table = Table(
                title="Findings by Provider",
                show_header=True,
                header_style="bold",
                border_style="blue",
            )

            provider_table.add_column("Provider", style="cyan")
            provider_table.add_column("Count", justify="right", style="yellow")

            for provider, count in sorted(
                summary.matches_by_provider.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                color = self._get_severity_color(provider)
                provider_table.add_row(
                    Text(provider.upper(), style=color),
                    str(count),
                )

            self.console.print(provider_table)

    def print_error(self, message: str) -> None:
        """Print an error message.

        Args:
            message: Error message to display.
        """
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message.

        Args:
            message: Warning message to display.
        """
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message.

        Args:
            message: Info message to display.
        """
        if self.verbose:
            self.console.print(f"[dim]{message}[/dim]")

    def create_progress(self, description: str = "Scanning...") -> Progress:  # noqa: ARG002
        """Create a progress indicator.

        Args:
            description: Description for the progress.

        Returns:
            Rich Progress instance.
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        )

    def print_file_matches(
        self,
        file_path: str,
        matches: list[ScanMatch],
    ) -> None:
        """Print matches grouped by file.

        Args:
            file_path: Path to the file.
            matches: List of matches in the file.
        """
        self.console.print()
        self.console.print(f"[bold blue]📁 {file_path}[/bold blue]")

        for match in matches:
            color = self._get_severity_color(match.provider)
            self.console.print(
                f"  [dim]Line {match.line_number}:[/dim] "
                f"[{color}]{match.provider.upper()}[/{color}] "
                f"[red]{match.redacted_value}[/red]"
            )


def create_console_reporter(
    verbose: bool = False,
    show_context: bool = True,
) -> ConsoleReporter:
    """Create a console reporter.

    Args:
        verbose: Whether to show verbose output.
        show_context: Whether to show context lines.

    Returns:
        Configured ConsoleReporter instance.
    """
    return ConsoleReporter(verbose=verbose, show_context=show_context)
