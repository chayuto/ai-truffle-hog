"""CLI application entry point."""

import typer

from ai_truffle_hog import __version__

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
    target: str = typer.Argument(
        ...,
        help="GitHub repository URL or file containing list of URLs",
    ),
    validate: bool = typer.Option(
        False,
        "--validate",
        "-v",
        help="Validate discovered keys against provider APIs",
    ),
    output: str = typer.Option(
        "table",
        "--output",
        "-o",
        help="Output format: table, json",
    ),
) -> None:
    """Scan repositories for AI API keys."""
    typer.echo(f"Scanning: {target}")
    typer.echo(f"Validate: {validate}")
    typer.echo(f"Output format: {output}")
    typer.echo("Scan command not yet implemented.")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
