#!/bin/bash
# UbShot Installer Script
# Downloads and installs UbShot with all dependencies

set -e

VERSION="1.0.1"
DEB_URL="https://github.com/bistaSananiJayesh/ubshot/releases/download/v${VERSION}/ubshot_${VERSION}_all.deb"
TMP_DIR=$(mktemp -d)

echo ""
echo "=========================================="
echo "     UbShot Installer v${VERSION}"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script needs sudo access to install."
    echo ""
    SUDO="sudo"
else
    SUDO=""
fi

# Download the package
echo "[1/3] Downloading UbShot..."
cd "$TMP_DIR"
if command -v wget &> /dev/null; then
    wget -q --show-progress -O ubshot.deb "$DEB_URL"
elif command -v curl &> /dev/null; then
    curl -L -o ubshot.deb "$DEB_URL"
else
    echo "Error: Neither wget nor curl found. Please install one."
    exit 1
fi

# Install with apt (handles dependencies automatically)
echo ""
echo "[2/3] Installing UbShot..."
$SUDO apt install -y ./ubshot.deb

# Cleanup
echo ""
echo "[3/3] Cleaning up..."
rm -rf "$TMP_DIR"

echo ""
echo "=========================================="
echo "  UbShot installed successfully!"
echo "=========================================="
echo ""
echo "  Run 'ubshot' or find it in your apps menu."
echo ""
echo "  Hotkeys:"
echo "    Ctrl+Shift+A - Capture area"
echo "    Ctrl+Shift+S - Capture fullscreen"
echo ""
