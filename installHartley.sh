#!/bin/bash
set -e

INSTALLER=$(realpath "$0")
INSTALL_DIR=$(dirname "$INSTALLER")
HARTLEY="$INSTALL_DIR/hartley"

echo "[*] Installing Hartley 2.0 (Gemini Terminal Agent)..."

# 1. Verify Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "[!] Error: Python 3 is required but not found. Please install Python 3 (e.g. via Homebrew: brew install python)."
    exit 1
fi

PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[+] Found Python $PYTHON_VER"

# 2. Ensure executable permissions
chmod +x "$HARTLEY"

# 3. Create destination directory and symlink
HARTLEY_TARGET_DIR="$HOME/.local/bin"
mkdir -p "$HARTLEY_TARGET_DIR"
ln -sf "$HARTLEY" "$HARTLEY_TARGET_DIR/hartley"

echo "[+] Linked $HARTLEY -> $HARTLEY_TARGET_DIR/hartley"

# 4. Check PATH
if [[ ":$PATH:" != *":$HARTLEY_TARGET_DIR:"* ]]; then
    echo ""
    echo "[!] Note: $HARTLEY_TARGET_DIR is not currently in your PATH."
    echo "    Add the following line to your ~/.zshrc (or ~/.bashrc):"
    echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "[OK] Hartley installed successfully!"
echo "     Run 'hartley --help' or simply 'hartley' to start the interactive agent."
echo "     Free Gemini API keys can be generated at: https://aistudio.google.com/app/apikey"
