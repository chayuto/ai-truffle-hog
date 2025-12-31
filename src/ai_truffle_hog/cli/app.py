"""CLI application entry point."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from ai_truffle_hog import __version__
from ai_truffle_hog.core.orchestrator import (
    OutputFormat,
    ScanResult,
    create_orchestrator,
)
from ai_truffle_hog.providers.registry import get_registry

app = typer.Typer(
    name="aitruffle",
    help="AI Truffle Hog - AI API Key Secret Scanner for GitHub Repositories",
    no_args_is_help=True,
    add_completion=False,
)


def _read_urls_from_file(file_path: Path) -> list[str]:
    """Read URLs from a file, ignoring comments and empty lines."""
    return [
        line.strip()
        for line in file_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def _is_url_list_file(target_path: Path) -> bool:
    """Check if target is a file containing list of URLs."""
    return (
        target_path.exists()
        and target_path.is_file()
        and target_path.suffix in (".txt", ".list")
    )


def _is_repository_url(target: str) -> bool:
    """Check if target is a repository URL."""
    return target.startswith(("http://", "https://", "git@"))


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo(f"AI Truffle Hog v{__version__}")


@app.command()
def scan(
    targets: Annotated[
        list[str],
        typer.Argument(
            help="GitHub repository URLs, local paths, or file containing list of URLs",
        ),
    ],
    validate: Annotated[
        bool,
        typer.Option(
            "--validate",
            "-v",
            help="Validate discovered keys against provider APIs",
        ),
    ] = False,
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Output format: table, json, sarif",
        ),
    ] = "table",
    providers: Annotated[
        str | None,
        typer.Option(
            "--providers",
            "-p",
            help="Comma-separated list of providers to scan for (default: all)",
        ),
    ] = None,
    output_file: Annotated[
        Path | None,
        typer.Option(
            "--output-file",
            "-f",
            help="Write output to file instead of stdout",
        ),
    ] = None,
    log_file: Annotated[
        Path | None,
        typer.Option(
            "--log-file",
            "-l",
            help="Write detailed scan log (files scanned, results) to file",
        ),
    ] = None,
    scan_history: Annotated[
        bool,
        typer.Option(
            "--history",
            "-H",
            help="Scan git history (ALL branches) for deleted secrets",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Show verbose output",
        ),
    ] = False,
) -> None:
    """Scan repositories or local paths for AI API keys.

    Supports multiple targets: URLs, local paths, or mixed.

    Examples:
        aitruffle scan https://github.com/user/repo
        aitruffle scan ./local-project
        aitruffle scan repo1-url repo2-url repo3-url
        aitruffle scan https://github.com/user/repo --history
        aitruffle scan . --output json --log-file scan.log
    """
    # Validate output format
    try:
        output_format = OutputFormat(output.lower())
    except ValueError:
        typer.echo(f"Invalid output format: {output}", err=True)
        typer.echo("Valid formats: table, json, sarif", err=True)
        raise typer.Exit(code=1) from None

    # Parse providers
    provider_list: list[str] | None = None
    if providers:
        provider_list = [p.strip() for p in providers.split(",")]

    # Create orchestrator
    orchestrator = create_orchestrator(
        validate=validate,
        output_format=output_format.value,
        providers=provider_list,
        verbose=verbose,
        scan_history=scan_history,
    )

    # Resolve targets to scan
    results = _resolve_and_scan_targets(targets, orchestrator)

    # Process and output results
    total_matches, any_failed = _process_scan_results(
        results, orchestrator, output_file, log_file
    )

    # Exit with error code if scan failed or secrets found
    if any_failed:
        raise typer.Exit(code=2)
    if total_matches > 0:
        raise typer.Exit(code=1)


def _resolve_and_scan_targets(targets: list[str], orchestrator) -> list[ScanResult]:
    """Resolve targets and perform scanning."""
    if len(targets) == 1:
        target = targets[0]
        target_path = Path(target)

        if _is_url_list_file(target_path):
            urls = _read_urls_from_file(target_path)
            return asyncio.run(orchestrator.scan_batch(urls))
        elif target_path.exists():
            result = asyncio.run(orchestrator.scan_local(target_path))
            return [result]
        elif _is_repository_url(target):
            result = asyncio.run(orchestrator.scan_repo(target))
            return [result]
        else:
            typer.echo(f"Invalid target: {target}", err=True)
            typer.echo("Target must be a valid local path or repository URL", err=True)
            raise typer.Exit(code=1)
    else:
        return asyncio.run(orchestrator.scan_batch(targets))


def _process_scan_results(
    results: list[ScanResult],
    orchestrator,
    output_file: Path | None,
    log_file: Path | None,
) -> tuple[int, bool]:
    """Process scan results and output them. Returns (total_matches, any_failed)."""
    total_matches = 0
    any_failed = False

    for result in results:
        if output_file:
            orchestrator.write_results(result, output_file)
        else:
            orchestrator.print_results(result)

        if log_file:
            orchestrator.write_scan_log(result, log_file)

        total_matches += result.total_matches
        if not result.success:
            any_failed = True

    if output_file:
        typer.echo(f"Results written to {output_file}")
    if log_file:
        typer.echo(f"Scan log written to {log_file}")

    return total_matches, any_failed


@app.command()
def providers() -> None:
    """List available providers."""
    registry = get_registry()
    all_providers = registry.all()

    typer.echo("Available AI API providers:")
    typer.echo()

    for provider in sorted(all_providers, key=lambda p: p.name):
        pattern_count = len(provider.patterns)
        typer.echo(
            f"  • {provider.display_name} ({provider.name}) - {pattern_count} pattern(s)"
        )

    typer.echo()
    typer.echo(f"Total: {len(all_providers)} providers")


if __name__ == "__main__":
    app()
