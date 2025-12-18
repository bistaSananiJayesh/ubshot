# UbShot

A **Shottr-like screenshot and annotation tool for Ubuntu Linux**.

> **Phase 3 - Advanced Tools**: Freehand, Highlighter, Spotlight, Blur, Steps, Ruler, Eyedropper.

## Features

### Current (Phase 3)
- 📷 **Area capture** - Select a region with dimmed overlay
- 🖥️ **Fullscreen capture** - Capture the screen where cursor is located
- ⚡ **Global hotkeys** - Works even when app is not focused (X11)
- 🔔 **System tray** - Quick access to capture actions
- 📋 **Auto-copy** - Screenshots automatically copied to clipboard
- 💾 **Auto-save** - Optional automatic saving to disk
- ✏️ **Annotation tools** - Rectangle, Ellipse, Arrow, Text
- 🖌️ **Freehand drawing** - Draw smooth freehand paths
- 🌟 **Highlighter** - Semi-transparent marker strokes
- 💡 **Spotlight** - Darken outside, highlight inside
- 🔲 **Blur/Pixelate** - Obscure sensitive content
- 🔢 **Step counter** - Numbered badges for instructions
- 📏 **Ruler** - Measure distances in pixels
- 🎨 **Eyedropper** - Pick colors from image
- 🧹 **Eraser** - Click to delete annotations
- 🔍 **Zoom/Pan** - Ctrl+wheel zoom, Space+drag pan
- ↩️ **Undo/Redo** - Full history support
- 🎨 **Properties panel** - Stroke, fill, opacity, font size

### Planned
- 🔤 OCR text recognition
- ☁️ Cloud upload integration
- 📸 Scrolling capture

## Quick Start

### 1. Create Virtual Environment

```bash
cd /path/to/shottr
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python -m src.app
```

The app runs in the system tray. Look for the camera icon!

## Usage

### Capture Flow

1. Press hotkey or use tray menu
2. For area capture: drag to select region (ESC to cancel)
3. **Editor opens with your screenshot**
4. Use toolbar to annotate (see shortcuts below)
5. Adjust properties in right panel
6. **Ctrl+S** to save

### Hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+A` | Area capture |
| `Ctrl+Shift+S` | Fullscreen capture |
| `V` | Pointer tool |
| `R` | Rectangle |
| `E` | Ellipse |
| `A` | Arrow |
| `T` | Text |
| `F` | Freehand |
| `H` | Highlighter |
| `S` | Spotlight |
| `B` | Blur |
| `N` | Step counter |
| `X` | Eraser |
| `I` | Eyedropper |
| `M` | Ruler |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+S` | Save |
| `Ctrl++/-/0` | Zoom in/out/100% |
| `Space+drag` | Pan canvas |
| `Ctrl+wheel` | Zoom at cursor |

### Editor Layout

```
┌─────────────────────────────────────────────────┐
│  [V] [R] [E] [A] [T]  [Crop] [↺] [↻]    [Save] │  ← Toolbar
├─────────────────────────────────────────────────┤
│                               │ Properties     │
│                               │ ─────────────  │
│         Canvas                │ Stroke: 3      │
│      (zoom & pan)             │ Color: ■       │
│                               │ Fill: None     │
│                               │ Opacity: 100   │
│                               │ Font: 18       │
├───────────────────────────────┴─────────────────┤
│  Zoom: 100%    1920 × 1080                     │  ← Status
└─────────────────────────────────────────────────┘
```

## Configuration

Settings: `~/.config/ubshot/config.json`

| Setting | Default | Description |
|---------|---------|-------------|
| `default_save_folder` | `~/Pictures/UbShot` | Save location |
| `auto_copy_to_clipboard` | `true` | Copy on capture |
| `auto_save` | `false` | Auto-save on capture |
| `hotkeys.capture_area` | `ctrl+shift+a` | Area hotkey |
| `hotkeys.capture_fullscreen` | `ctrl+shift+s` | Fullscreen hotkey |

## Project Structure

```
src/
├── app.py                    # Entry point
├── core/
│   ├── app_core.py           # Application orchestration
│   ├── capture_service.py    # Screenshot capture
│   ├── selection_overlay.py  # Area selection UI
│   ├── tray_service.py       # System tray
│   └── hotkey_service.py     # Global hotkeys
├── ui/
│   └── main_window.py        # Main window
├── editor/
│   ├── editor_widget.py      # Complete editor UI
│   ├── editor_canvas.py      # Canvas with zoom/pan
│   ├── annotations.py        # Annotation models
│   └── tools.py              # Tool framework
└── services/
    ├── config_service.py     # Configuration
    └── logging_service.py    # Logging
```

## Logs

Logs: `~/.local/share/ubshot/logs/`

## Troubleshooting

### Hotkeys not working?
- Ensure X11 session (not Wayland)
- Check pynput installed: `pip install pynput`

### Tray icon not visible?
- GNOME: Install "AppIndicator" extension

## Development Roadmap

| Phase | Status | Focus |
|-------|--------|-------|
| Phase 0 | ✅ Done | Project foundation |
| Phase 1 | ✅ Done | Tray, hotkeys, capture |
| **Phase 2** | ✅ Done | Editor, tools, undo/redo |
| Phase 3 | 🔜 Next | Advanced tools, effects |
| Phase 4 | Planned | OCR, QR, cloud upload |

---

*Inspired by [Shottr](https://shottr.cc/) for macOS.*
