# UbShot

A **Shottr-like screenshot and annotation tool for Ubuntu Linux**.

![UbShot](https://raw.githubusercontent.com/bistaSananiJayesh/ubshot/main/src/resources/icons/app_icon.png)

## ✨ Features

- 📷 **Area capture** - Select a region with dimmed overlay
- 🖥️ **Fullscreen capture** - Capture entire screen
- ⚡ **Global hotkeys** - Works even when app is not focused
- 📋 **Auto-copy** - Screenshots automatically copied to clipboard
- 💾 **Auto-save** - Automatic saving to disk
- ✏️ **Annotation tools** - Rectangle, Ellipse, Arrow, Text
- 🖌️ **Freehand drawing** - Smooth freehand paths
- 🌟 **Highlighter** - Semi-transparent marker
- 💡 **Spotlight** - Darken outside, highlight inside
- 🔲 **Blur** - Obscure sensitive content
- 🔢 **Step counter** - Numbered badges for instructions
- ↩️ **Undo/Redo** - Full history support
- 🔔 **System tray** - Quick access to capture actions

## 🚀 Quick Install (One Command)

```bash
curl -sSL https://raw.githubusercontent.com/bistaSananiJayesh/ubshot/main/install.sh | sudo bash
```

Or with wget:
```bash
wget -qO- https://raw.githubusercontent.com/bistaSananiJayesh/ubshot/main/install.sh | sudo bash
```

## 📦 Manual Installation

### Option 1: Download .deb Package

```bash
# Download
wget https://github.com/bistaSananiJayesh/ubshot/releases/latest/download/ubshot_1.0.1_all.deb

# Install (automatically handles dependencies)
sudo apt install ./ubshot_1.0.1_all.deb
```

### Option 2: Run from Source

```bash
git clone https://github.com/bistaSananiJayesh/ubshot.git
cd ubshot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.app
```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+A` | Capture Area |
| `Ctrl+Shift+S` | Capture Fullscreen |
| `Ctrl+C` | Copy to Clipboard |
| `Ctrl+S` | Save |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Delete` | Delete Selected |
| `Space + Drag` | Pan Canvas |
| `Ctrl + Scroll` | Zoom |

## 🛠️ Tool Shortcuts

| Key | Tool |
|-----|------|
| `V` | Pointer |
| `R` | Rectangle |
| `E` | Ellipse |
| `A` | Arrow |
| `T` | Text |
| `F` | Freehand |
| `H` | Highlighter |
| `O` | Spotlight |
| `B` | Blur |
| `N` | Step Counter |

## 📋 Requirements

- Ubuntu 22.04+ / Debian 12+
- Python 3.10+
- X11 (for global hotkeys)

## 🗑️ Uninstall

```bash
sudo apt remove ubshot
```

## 📄 License

MIT License - feel free to use, modify, and distribute.

## 🙏 Credits

Inspired by [Shottr](https://shottr.cc/) - the best screenshot tool for macOS.
