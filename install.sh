#!/bin/sh
# SeeForce CLI installer
# Usage: curl -fsSL https://seeforce.io/install.sh | sh
set -e

REPO="https://github.com/SilversMind/seeforce-cli.git"
PKG="git+${REPO}#subdirectory=cli"

echo "Installing SeeForce CLI..."

if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found — installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv tool install "$PKG" --force

echo ""
echo "SeeForce CLI installed. Run: seeforce --help"
echo ""
echo "Get started:"
echo "  1. seeforce login"
echo "  2. seeforce mcp install"
echo "  3. Ask your AI assistant: 'Annotate my codebase with Seeforce'"
echo "  4. seeforce scan ."
