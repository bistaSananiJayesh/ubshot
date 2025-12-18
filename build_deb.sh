#!/bin/bash
# UbShot Debian Package Build Script (Lightweight version)
# Creates a .deb package that installs dependencies at runtime

set -e

APP_NAME="ubshot"
VERSION="1.0.0"
ARCH="all"
MAINTAINER="Jayesh Sangani <jayesh@example.com>"
DESCRIPTION="UbShot - Screenshot & Annotation Tool for Linux"

# Directories
BUILD_DIR="build/deb"
PKG_DIR="${BUILD_DIR}/${APP_NAME}_${VERSION}_${ARCH}"

echo "🚀 Building UbShot Debian Package v${VERSION} (lightweight)..."

# Clean previous builds
rm -rf "${BUILD_DIR}"
mkdir -p "${PKG_DIR}"

# Create directory structure
mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/opt/ubshot"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps"

# Copy application files (excluding venv and build artifacts)
echo "📦 Copying application files..."
cp -r src "${PKG_DIR}/opt/ubshot/"
cp requirements.txt "${PKG_DIR}/opt/ubshot/"
cp README.md "${PKG_DIR}/opt/ubshot/" 2>/dev/null || true

# Create launcher script
cat > "${PKG_DIR}/usr/bin/ubshot" << 'EOF'
#!/bin/bash
cd /opt/ubshot
if [ ! -d "venv" ]; then
    echo "First run: Setting up virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --quiet -r requirements.txt
else
    source venv/bin/activate
fi
python -m src.app "$@"
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

# Create DEBIAN control file
cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${VERSION}
Section: graphics
Priority: optional
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Depends: python3 (>= 3.10), python3-venv, python3-pip
Description: ${DESCRIPTION}
 A Shottr-like screenshot and annotation tool for Linux.
 Features: Area/fullscreen capture, annotations (shapes, arrows, text),
 blur/spotlight effects, auto-copy to clipboard, global hotkeys.
EOF

# Create post-install script
cat > "${PKG_DIR}/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e
echo "✅ UbShot installed successfully!"
echo "   Setting up virtual environment on first run..."
echo ""
echo "   Run 'ubshot' or find it in your applications menu."
EOF
chmod +x "${PKG_DIR}/DEBIAN/postinst"

# Create post-remove script
cat > "${PKG_DIR}/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e
if [ "$1" = "purge" ]; then
    rm -rf /opt/ubshot
fi
EOF
chmod +x "${PKG_DIR}/DEBIAN/postrm"

# Build the package
echo "🔨 Building .deb package..."
dpkg-deb --build --root-owner-group "${PKG_DIR}"

# Move to dist folder
mkdir -p dist
mv "${PKG_DIR}.deb" "dist/${APP_NAME}_${VERSION}_${ARCH}.deb"

# Show package size
PACKAGE_SIZE=$(du -h "dist/${APP_NAME}_${VERSION}_${ARCH}.deb" | cut -f1)

echo ""
echo "✅ Package built successfully!"
echo "   📦 dist/${APP_NAME}_${VERSION}_${ARCH}.deb (${PACKAGE_SIZE})"
echo ""
echo "To install: sudo dpkg -i dist/${APP_NAME}_${VERSION}_${ARCH}.deb"
echo "To remove:  sudo apt remove ubshot"
