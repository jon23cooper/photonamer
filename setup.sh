#!/bin/bash
set -e

echo "=== PhotoNamer Setup ==="

# Check Homebrew
if ! command -v brew &>/dev/null; then
  echo "Homebrew not found. Install it from https://brew.sh, then re-run this script."
  exit 1
fi

# Install exiftool
if ! command -v exiftool &>/dev/null; then
  echo "Installing exiftool..."
  brew install exiftool
else
  echo "exiftool already installed: $(exiftool -ver)"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

echo "Installing Python dependencies..."
.venv/bin/pip install --upgrade pip -q
# PySide6 bundles QtWebEngine — no separate package needed
.venv/bin/pip install -r requirements.txt

echo ""
echo "=== Setup complete ==="
echo ""
echo "To launch PhotoNamer, run:"
echo "  .venv/bin/python main.py"
echo ""
echo "Or add this alias to your shell profile:"
echo "  alias photonamer='cd $(pwd) && .venv/bin/python main.py'"
