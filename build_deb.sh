#!/bin/bash
# UbShot Debian Package Build Script (FULLY BUNDLED)
# Creates a .deb package with all dependencies included - works on any system

set -e

APP_NAME="ubshot"
VERSION="1.1.0"
ARCH="amd64"
MAINTAINER="Jayesh Sangani <jayesh@example.com>"
DESCRIPTION="UbShot - Screenshot & Annotation Tool for Linux"

# Directories
BUILD_DIR="build/deb"
PKG_DIR="${BUILD_DIR}/${APP_NAME}_${VERSION}_${ARCH}"

echo "🚀 Building UbShot Debian Package v${VERSION} (fully bundled)..."
echo "   This creates a larger package but works on any system."
echo ""

# Clean previous builds
rm -rf "${BUILD_DIR}"
mkdir -p "${PKG_DIR}"

# Create directory structure
mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/opt/ubshot"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps"

# Copy application files
echo "📦 Copying application files..."
cp -r src "${PKG_DIR}/opt/ubshot/"
cp requirements.txt "${PKG_DIR}/opt/ubshot/"
cp README.md "${PKG_DIR}/opt/ubshot/" 2>/dev/null || true

# Create and populate virtual environment
echo "📥 Creating virtual environment with all dependencies..."
echo "   (This may take a few minutes)"
python3 -m venv "${PKG_DIR}/opt/ubshot/venv"
source "${PKG_DIR}/opt/ubshot/venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
deactivate

# Make venv paths relative (important for portability)
echo "🔧 Making virtual environment portable..."
# Fix shebang paths in venv scripts to be relative
find "${PKG_DIR}/opt/ubshot/venv/bin" -type f -exec sed -i "s|${PKG_DIR}||g" {} \; 2>/dev/null || true

# Create launcher script (simple, no first-run setup needed)
cat > "${PKG_DIR}/usr/bin/ubshot" << 'EOF'
#!/bin/bash
# UbShot Launcher

export PATH="/opt/ubshot/venv/bin:$PATH"
cd /opt/ubshot
/opt/ubshot/venv/bin/python3 -m src.app "$@"
EOF
chmod +x "${PKG_DIR}/usr/bin/ubshot"

# Create desktop entry
cat > "${PKG_DIR}/usr/share/applications/ubshot.desktop" << EOF
[Desktop Entry]
Name=UbShot
Comment=Screenshot & Annotation Tool
Exec=/usr/bin/ubshot
Icon=ubshot
Type=Application
Categories=Graphics;Utility;
Keywords=screenshot;capture;annotate;snip;
StartupWMClass=UbShot
Terminal=false
EOF

# Copy icon
if [ -f "src/resources/icons/app_icon.png" ]; then
    cp "src/resources/icons/app_icon.png" "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps/ubshot.png"
    echo "✓ App icon copied"
fi

# Calculate installed size in KB
INSTALLED_SIZE=$(du -sk "${PKG_DIR}" | cut -f1)

# Create DEBIAN control file (minimal dependencies)
cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: graphics
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_SIZE}
Maintainer: ${MAINTAINER}
Depends: python3 (>= 3.10), libxcb-cursor0, libxcb-xinerama0
Description: ${DESCRIPTION}
 A Shottr-like screenshot and annotation tool for Linux.
 Features: Area/fullscreen capture, annotations (shapes, arrows, text),
 blur/spotlight effects, auto-copy to clipboard, global hotkeys.
 .
 This package includes all dependencies - works out of the box!
EOF

# Create post-install script
cat > "${PKG_DIR}/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e
echo ""
echo "✅ UbShot installed successfully!"
echo ""
echo "   Run 'ubshot' or find it in your applications menu."
echo "   Global hotkeys: Ctrl+Shift+A (area), Ctrl+Shift+S (fullscreen)"
echo ""
EOF
chmod +x "${PKG_DIR}/DEBIAN/postinst"

# Create post-remove script
cat > "${PKG_DIR}/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e
if [ "$1" = "purge" ]; then
    rm -rf /opt/ubshot
    rm -rf "$HOME/.local/share/ubshot" 2>/dev/null || true
fi
EOF
chmod +x "${PKG_DIR}/DEBIAN/postrm"

# Build the package
echo ""
echo "🔨 Building .deb package (this may take a moment for compression)..."
dpkg-deb --build --root-owner-group "${PKG_DIR}"

# Move to dist folder
mkdir -p dist
mv "${PKG_DIR}.deb" "dist/${APP_NAME}_${VERSION}_${ARCH}.deb"

# Show package size
PACKAGE_SIZE=$(du -h "dist/${APP_NAME}_${VERSION}_${ARCH}.deb" | cut -f1)

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Package built successfully!"
echo ""
echo "   📦 dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "   📊 Size: ${PACKAGE_SIZE}"
echo ""
echo "   This package includes ALL dependencies - works on any Ubuntu!"
echo ""
echo "To install: sudo apt install ./dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "To remove:  sudo apt remove ubshot"
echo "════════════════════════════════════════════════════════════════"
