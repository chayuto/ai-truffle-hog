#!/usr/bin/env bash
# Development environment setup script for AI Truffle Hog
# Run this script to set up your local development environment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

log_info "Setting up AI Truffle Hog development environment..."
echo ""

# Check Python version
log_info "Checking Python version..."
REQUIRED_PYTHON_VERSION="3.11"

if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ "$PYTHON_VERSION" < "$REQUIRED_PYTHON_VERSION" ]]; then
        log_error "Python $REQUIRED_PYTHON_VERSION or higher is required. Found: $PYTHON_VERSION"
        exit 1
    fi
else
    log_error "Python 3 is not installed. Please install Python $REQUIRED_PYTHON_VERSION or higher."
    exit 1
fi

log_success "Using $($PYTHON_CMD --version)"

# Create virtual environment if it doesn't exist
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    log_info "Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    log_success "Virtual environment created at $VENV_DIR"
else
    log_info "Virtual environment already exists at $VENV_DIR"
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
log_info "Upgrading pip..."
pip install --upgrade pip --quiet

# Install package in editable mode with dev dependencies
log_info "Installing package with development dependencies..."
pip install -e ".[dev]" --quiet

log_success "Package installed successfully"

# Install pre-commit hooks
if command -v pre-commit &> /dev/null; then
    log_info "Installing pre-commit hooks..."
    pre-commit install
    log_success "Pre-commit hooks installed"
else
    log_warn "pre-commit not found in PATH, skipping hook installation"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        log_info "Creating .env file from .env.example..."
        cp .env.example .env
        log_success ".env file created (please update with your values)"
    fi
else
    log_info ".env file already exists"
fi

# Create logs directory
mkdir -p logs

# Print summary
echo ""
echo "=============================================="
log_success "Development environment setup complete!"
echo "=============================================="
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run the CLI:"
echo "  ai-truffle-hog --help"
echo "  # or"
echo "  ath --help"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
echo "To run linting:"
echo "  ruff check src tests"
echo "  ruff format src tests"
echo ""
echo "To run type checking:"
echo "  mypy src"
echo ""
echo "Happy hacking! 🐷🔍"
