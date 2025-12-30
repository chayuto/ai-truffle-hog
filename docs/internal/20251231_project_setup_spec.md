# AI-Truffle-Hog: Project Setup Specification

**Document Version:** 1.0  
**Date:** 2025-12-31  
**Author:** Architecture Analysis  
**Status:** Implementation Specification

---

## 1. Overview

This document provides the exact specifications for setting up the Python project structure, virtual environment, and development tooling for the AI-Truffle-Hog POC.

---

## 2. Project Structure

### 2.1 Complete Directory Tree

```
ai-truffle-hog/
├── .github/
│   └── workflows/
│       └── ci.yml                    # GitHub Actions CI
├── .vscode/
│   └── settings.json                 # VS Code project settings
├── docs/
│   ├── internal/                     # Internal planning docs
│   ├── personal/                     # Personal notes
│   └── research/                     # Research documents
├── src/
│   └── ai_truffle_hog/
│       ├── __init__.py
│       ├── __main__.py               # CLI entry point
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py                # Typer application
│       │   └── commands/
│       │       ├── __init__.py
│       │       └── scan.py           # Scan command
│       ├── core/
│       │   ├── __init__.py
│       │   ├── orchestrator.py       # Scan orchestration
│       │   ├── scanner.py            # Pattern matching
│       │   └── models.py             # Data models
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py               # Abstract base provider
│       │   ├── registry.py           # Provider registry
│       │   ├── openai.py
│       │   ├── anthropic.py
│       │   ├── huggingface.py
│       │   ├── cohere.py
│       │   ├── replicate.py
│       │   ├── google.py
│       │   ├── groq.py
│       │   └── langsmith.py
│       ├── fetcher/
│       │   ├── __init__.py
│       │   ├── git.py                # Git operations
│       │   └── file_walker.py        # File enumeration
│       ├── validator/
│       │   ├── __init__.py
│       │   ├── client.py             # Async HTTP validation
│       │   └── rate_limiter.py       # Rate limiting
│       ├── reporter/
│       │   ├── __init__.py
│       │   ├── console.py            # Console output
│       │   ├── json_reporter.py      # JSON output
│       │   └── log_handler.py        # Logging setup
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── config.py             # Configuration
│       │   ├── redaction.py          # Secret redaction
│       │   └── entropy.py            # Entropy calculation
│       └── config/
│           ├── default.toml          # Default config
│           └── patterns.toml         # Provider patterns
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_scanner.py
│   │   ├── test_entropy.py
│   │   ├── test_redaction.py
│   │   └── test_models.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_git.py
│   │   └── test_file_walker.py
│   └── e2e/
│       ├── __init__.py
│       └── test_scan_command.py
├── scripts/
│   └── dev_setup.sh                  # Development setup script
├── .env.example                      # Example environment variables
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version                   # Python version for pyenv
├── LICENSE
├── README.md
├── pyproject.toml                    # Project configuration
└── uv.lock                           # Lock file (if using uv)
```

---

## 3. Python Environment Specification

### 3.1 Python Version

```
Python >= 3.11
```

**Rationale:**
- Native TOML support (`tomllib`)
- Performance improvements
- Better error messages
- Type hint improvements

### 3.2 Virtual Environment Setup

**Using venv (standard):**
```bash
cd /path/to/ai-truffle-hog
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux
```

**Using uv (recommended for speed):**
```bash
uv venv --python 3.11
source .venv/bin/activate
```

---

## 4. pyproject.toml Specification

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ai-truffle-hog"
version = "0.1.0"
description = "AI API Key Secret Scanner for GitHub Repositories"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [
    { name = "Your Name", email = "your.email@example.com" }
]
keywords = ["security", "secrets", "api-keys", "scanner", "openai", "anthropic"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Intended Audience :: Information Technology",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Security",
    "Topic :: Software Development :: Quality Assurance",
    "Typing :: Typed",
]

dependencies = [
    "typer[all]>=0.12.0",
    "httpx>=0.27.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    "structlog>=24.2.0",
    "gitpython>=3.1.43",
    "rich>=13.7.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.7",
    "pytest-cov>=5.0.0",
    "respx>=0.21.1",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
    "pre-commit>=3.7.1",
]

[project.scripts]
aitruffle = "ai_truffle_hog.cli.app:app"
ai-truffle-hog = "ai_truffle_hog.cli.app:app"

[project.urls]
Homepage = "https://github.com/yourusername/ai-truffle-hog"
Documentation = "https://github.com/yourusername/ai-truffle-hog#readme"
Repository = "https://github.com/yourusername/ai-truffle-hog.git"
Issues = "https://github.com/yourusername/ai-truffle-hog/issues"

[tool.hatch.build.targets.wheel]
packages = ["src/ai_truffle_hog"]

[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "PTH",    # flake8-use-pathlib
    "ERA",    # eradicate
    "RUF",    # ruff-specific rules
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # do not perform function calls in argument defaults
]

[tool.ruff.lint.isort]
known-first-party = ["ai_truffle_hog"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["git.*", "structlog.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "e2e: marks tests as end-to-end tests",
]

[tool.coverage.run]
source = ["src/ai_truffle_hog"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
]
```

---

## 5. Configuration Files

### 5.1 .gitignore

```gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/
env/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Ruff
.ruff_cache/

# Logs
*.log
logs/

# Local configuration
.env
.env.local

# OS
.DS_Store
Thumbs.db

# Project specific
temp_repos/
scan_results/
```

### 5.2 .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.7.0
          - typer>=0.12.0
          - types-toml
```

### 5.3 .python-version

```
3.11
```

### 5.4 .env.example

```bash
# AI Truffle Hog Configuration
# Copy to .env and fill in values

# Logging
ATH_LOG_LEVEL=INFO
ATH_LOG_FORMAT=json
ATH_LOG_FILE=ai-truffle-hog.log

# Validation
ATH_VALIDATE_ENABLED=true
ATH_VALIDATE_TIMEOUT=10
ATH_VALIDATE_MAX_CONCURRENT=5

# Scanner
ATH_SCANNER_ENTROPY_THRESHOLD=4.5
ATH_SCANNER_MAX_FILE_SIZE_KB=1024

# Output
ATH_OUTPUT_FORMAT=table
ATH_OUTPUT_SHOW_CONTEXT=true

# Proxy (optional, for validation)
# ATH_PROXY_URL=http://proxy:8080
```

---

## 6. VS Code Settings

### 6.1 .vscode/settings.json

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    },
    
    "python.testing.pytestEnabled": true,
    "python.testing.pytestPath": "${workspaceFolder}/.venv/bin/pytest",
    "python.testing.pytestArgs": [
        "tests",
        "-v"
    ],
    
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/.mypy_cache": true,
        "**/.ruff_cache": true,
        "**/*.egg-info": true
    },
    
    "editor.rulers": [100],
    
    "ruff.organizeImports": true,
    "ruff.fixAll": true
}
```

---

## 7. Development Scripts

### 7.1 scripts/dev_setup.sh

```bash
#!/bin/bash
set -euo pipefail

echo "🔧 Setting up AI Truffle Hog development environment..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "📦 Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -e ".[dev]"

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
fi

echo ""
echo "✨ Development environment setup complete!"
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the CLI:"
echo "  aitruffle --help"
echo ""
echo "To run tests:"
echo "  pytest"
```

---

## 8. GitHub Actions CI

### 8.1 .github/workflows/ci.yml

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      
      - name: Install dependencies
        run: uv pip install --system -e ".[dev]"
      
      - name: Run Ruff
        run: ruff check .
      
      - name: Run Ruff Format
        run: ruff format --check .

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      
      - name: Install dependencies
        run: uv pip install --system -e ".[dev]"
      
      - name: Run mypy
        run: mypy src/

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      
      - name: Install dependencies
        run: uv pip install --system -e ".[dev]"
      
      - name: Run tests
        run: pytest --cov=src/ai_truffle_hog --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.11'
        with:
          files: coverage.xml
```

---

## 9. Initial README.md Template

```markdown
# AI Truffle Hog 🐷🔑

> AI API Key Secret Scanner for GitHub Repositories

[![CI](https://github.com/yourusername/ai-truffle-hog/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/ai-truffle-hog/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

AI Truffle Hog is a specialized secret scanner designed to detect leaked AI provider API keys in GitHub repositories. It supports:

- **OpenAI** (sk-, sk-proj-, sk-org-)
- **Anthropic** (sk-ant-api03-)
- **Hugging Face** (hf_)
- **Cohere**
- **Replicate** (r8_)
- **Google Gemini** (AIza)
- **Groq** (gsk_)
- **LangSmith** (lsv2_)
- And more...

## Installation

```bash
pip install ai-truffle-hog
```

## Quick Start

```bash
# Scan a single repository
aitruffle scan https://github.com/user/repo

# Scan with validation
aitruffle scan https://github.com/user/repo --validate

# Scan from a list of URLs
aitruffle scan repos.txt

# Output as JSON
aitruffle scan https://github.com/user/repo --output json
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-truffle-hog.git
cd ai-truffle-hog

# Run setup script
chmod +x scripts/dev_setup.sh
./scripts/dev_setup.sh

# Activate virtual environment
source .venv/bin/activate

# Run tests
pytest
```

## License

MIT License - see [LICENSE](LICENSE) for details.
```

---

## 10. Dependency Lock Strategy

### Option A: pip-tools (Recommended for simplicity)
```bash
pip install pip-tools
pip-compile pyproject.toml -o requirements.lock
pip-compile pyproject.toml --extra dev -o requirements-dev.lock
```

### Option B: uv (Recommended for speed)
```bash
uv lock
```

### Option C: poetry
Alternative if team prefers poetry's workflow.

---

## 11. Setup Verification Checklist

After running setup, verify:

- [ ] `.venv/` directory exists
- [ ] `which python` points to `.venv/bin/python`
- [ ] `pip list` shows all dependencies
- [ ] `aitruffle --help` works
- [ ] `pytest` runs without errors
- [ ] `ruff check .` passes
- [ ] `mypy src/` passes
- [ ] `pre-commit run --all-files` passes
