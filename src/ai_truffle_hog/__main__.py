"""Entry point for running AI Truffle Hog as a module.

Usage:
    python -m ai_truffle_hog [OPTIONS] COMMAND [ARGS]...
"""

from ai_truffle_hog.cli.app import app

if __name__ == "__main__":
    app()
