"""CLI application entry point."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from ai_truffle_hog import __version__
from ai_truffle_hog.core.orchestrator import OutputFormat, create_orchestrator
from ai_truffle_hog.providers.registry import get_registry

app = typer.Typer(
    name="aitruffle",
    help="AI Truffle Hog - AI API Key Secret Scanner for GitHub Repositories",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo(f"AI Truffle Hog v{__version__}")


@app.command()
def scan(
    target: Annotated[
        str,
        typer.Argument(
            help="GitHub repository URL, local path, or file containing list of URLs",
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
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Show verbose output",
        ),
    ] = False,
) -> None:
    """Scan repositories or local paths for AI API keys."""
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
    )

    # Determine target type and scan
    target_path = Path(target)

    if target_path.exists():
        # Local path
        result = asyncio.run(orchestrator.scan_local(target_path))
    elif target.startswith(("http://", "https://", "git@")):
        # Repository URL
        result = asyncio.run(orchestrator.scan_repo(target))
    else:
        typer.echo(f"Invalid target: {target}", err=True)
        typer.echo("Target must be a valid local path or repository URL", err=True)
        raise typer.Exit(code=1)

    # Output results
    if output_file:
        orchestrator.write_results(result, output_file)
        typer.echo(f"Results written to {output_file}")
    else:
        orchestrator.print_results(result)

    # Exit with error code if scan failed or secrets found
    if not result.success:
        raise typer.Exit(code=2)
    if result.total_matches > 0:
        raise typer.Exit(code=1)


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
