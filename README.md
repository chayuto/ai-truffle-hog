# AI Truffle Hog 🐷🔍

> Sniff out exposed AI provider API keys in your codebases

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

AI Truffle Hog is a specialized security tool designed to detect exposed AI provider API keys in source code repositories. It supports multiple AI providers and can optionally validate whether detected keys are still active.

## Features

- 🔍 **Multi-Provider Detection**: Supports OpenAI, Anthropic, Google AI, Cohere, Mistral, Hugging Face, Replicate, Together AI, and more
- ✅ **Key Validation**: Optionally verify if detected keys are still active (with rate limiting)
- 📊 **Entropy Analysis**: Uses Shannon entropy to reduce false positives
- 🚀 **Fast Scanning**: Async I/O for efficient file processing
- 📝 **Structured Logging**: JSON logging with secret redaction
- 🎨 **Beautiful Output**: Rich console output with tables and colors

## Installation

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/ai-truffle-hog/ai-truffle-hog.git
cd ai-truffle-hog

# Run the setup script
./scripts/dev_setup.sh

# Or manually:
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick Start

```bash
# Scan a local directory
ai-truffle-hog scan /path/to/code

# Scan a GitHub repository
ai-truffle-hog scan https://github.com/user/repo

# Scan with validation enabled
ai-truffle-hog scan /path/to/code --validate

# Output as JSON
ai-truffle-hog scan /path/to/code --output json

# Short alias
ath scan /path/to/code
```

## Supported Providers

| Provider | Key Pattern | Validation |
|----------|-------------|------------|
| OpenAI | `sk-proj-*`, `sk-*` | ✅ |
| Anthropic | `sk-ant-api*` | ✅ |
| Google AI | `AIza*` | ✅ |
| Cohere | Custom pattern | ✅ |
| Mistral | Custom pattern | ✅ |
| Hugging Face | `hf_*` | ✅ |
| Replicate | `r8_*` | ✅ |
| Together AI | Custom pattern | ✅ |

## Configuration

Configuration can be set via environment variables or a TOML config file:

```bash
# Environment variables (prefix: ATH_)
export ATH_SCANNER_ENTROPY_THRESHOLD=4.5
export ATH_VALIDATOR_ENABLED=true
export ATH_LOGGING_LEVEL=DEBUG
```

See [.env.example](.env.example) for all available options.

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=ai_truffle_hog

# Lint code
ruff check src tests

# Format code
ruff format src tests

# Type checking
mypy src

# Run all pre-commit hooks
pre-commit run --all-files
```

## Project Structure

```
ai-truffle-hog/
├── src/ai_truffle_hog/
│   ├── cli/           # CLI commands (Typer)
│   ├── core/          # Core models and orchestration
│   ├── providers/     # AI provider implementations
│   ├── fetcher/       # Git clone and file walking
│   ├── validator/     # Key validation with rate limiting
│   ├── reporter/      # Output formatting
│   └── utils/         # Utilities (config, entropy, redaction)
├── tests/
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── e2e/           # End-to-end tests
├── docs/              # Documentation
└── scripts/           # Development scripts
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting a pull request.

## Security

If you discover a security vulnerability, please report it responsibly. Do not open a public issue.

---

*Built with 🐷 for the security-conscious AI developer*
