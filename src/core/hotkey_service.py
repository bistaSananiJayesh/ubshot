"""
Global hotkey service for UbShot application.

This module provides global hotkey registration and handling using the
pynput library for X11 systems. Hotkeys work even when the application
window is not focused.

Note: This implementation is X11-only. Wayland support will require a
different approach (e.g., using portal APIs) and is deferred to later phases.
"""

import threading
from typing import Callable, Dict, Optional, Set

from PySide6.QtCore import QMetaObject, QObject, Qt, Signal, Slot

from src.services.config_service import ConfigService
from src.services.logging_service import get_logger

# Try to import pynput for global hotkeys
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


class HotkeyService(QObject):
    """
    Global hotkey registration and handling service.

    Uses pynput to listen for global keyboard shortcuts on X11.
    When a registered hotkey is pressed, the corresponding Qt signal
    is emitted on the main thread.

    Signals:
        area_capture_triggered: Emitted when area capture hotkey is pressed.
        fullscreen_capture_triggered: Emitted when fullscreen capture hotkey is pressed.

    Note:
        - Requires pynput library for global hotkeys
        - X11 only; Wayland requires different approach
        - Hotkeys work even when app is not focused
    """

    area_capture_triggered = Signal()
    fullscreen_capture_triggered = Signal()

    def __init__(
        self,
        config_service: ConfigService,
        parent: Optional[QObject] = None
    ) -> None:
        """
        Initialize the hotkey service.

        Args:
            config_service: The config service to read hotkey settings from.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._logger = get_logger(__name__)
        self._config = config_service

        # Hotkey state tracking
        self._listener: Optional[keyboard.Listener] = None
        self._current_keys: Set[keyboard.Key | keyboard.KeyCode] = set()
        self._hotkeys: Dict[frozenset, str] = {}  # Maps key combos to action names

        # Thread safety
        self._lock = threading.Lock()

        if not PYNPUT_AVAILABLE:
            self._logger.warning(
                "pynput not available. Global hotkeys will not work. "
                "Install with: pip install pynput"
            )
            return

        self._setup_hotkeys()
        self._start_listener()

    def _parse_hotkey(self, hotkey_str: str) -> frozenset:
        """
        Parse a hotkey string like "ctrl+shift+a" into a set of keys.

        Args:
            hotkey_str: The hotkey string (e.g., "ctrl+shift+a").

        Returns:
            A frozenset of pynput key objects.
        """
        keys = set()
        parts = hotkey_str.lower().split("+")

        for part in parts:
            part = part.strip()
            if part in ("ctrl", "control"):
                keys.add(keyboard.Key.ctrl_l)
            elif part in ("shift",):
                keys.add(keyboard.Key.shift_l)
            elif part in ("alt",):
                keys.add(keyboard.Key.alt_l)
            elif part in ("super", "win", "cmd"):
                keys.add(keyboard.Key.cmd)
            elif len(part) == 1:
                # Single character key
                keys.add(keyboard.KeyCode.from_char(part))
            else:
                self._logger.warning(f"Unknown key in hotkey string: {part}")

        return frozenset(keys)

    def _setup_hotkeys(self) -> None:
        """Set up hotkey mappings from config."""
        # Get hotkey strings from config
        area_hotkey = self._config.hotkey_capture_area
        fullscreen_hotkey = self._config.hotkey_capture_fullscreen

        self._logger.info(f"Setting up hotkeys: area={area_hotkey}, fullscreen={fullscreen_hotkey}")

        # Parse and store hotkey mappings
        self._hotkeys = {
            self._parse_hotkey(area_hotkey): "capture_area",
            self._parse_hotkey(fullscreen_hotkey): "capture_fullscreen",
        }

        self._logger.debug(f"Parsed hotkey mappings: {self._hotkeys}")

    def _start_listener(self) -> None:
        """Start the global keyboard listener in a background thread."""
        if not PYNPUT_AVAILABLE:
            return

        self._logger.debug("Starting global hotkey listener")

        self._listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._listener.daemon = True
        self._listener.start()

        self._logger.info("Global hotkey listener started")

    def _on_key_press(self, key) -> None:
        """Handle key press events from pynput."""
        with self._lock:
            # Normalize key (handle both left and right modifiers)
            normalized_key = self._normalize_key(key)
            self._current_keys.add(normalized_key)

            # Check if current keys match any registered hotkey
            current_combo = frozenset(self._current_keys)

            for hotkey_combo, action in self._hotkeys.items():
                if self._combo_matches(hotkey_combo, current_combo):
                    self._logger.debug(f"Hotkey matched: {action}")
                    self._trigger_action(action)
                    break

    def _on_key_release(self, key) -> None:
        """Handle key release events from pynput."""
        with self._lock:
            normalized_key = self._normalize_key(key)
            self._current_keys.discard(normalized_key)

    def _normalize_key(self, key) -> keyboard.Key | keyboard.KeyCode:
        """
        Normalize a key to handle left/right modifier variants.

        Args:
            key: The pynput key object.

        Returns:
            Normalized key (left variant for modifiers).
        """
        if not PYNPUT_AVAILABLE:
            return key

        # Map right modifiers to left equivalents
        modifier_map = {
            keyboard.Key.ctrl_r: keyboard.Key.ctrl_l,
            keyboard.Key.shift_r: keyboard.Key.shift_l,
            keyboard.Key.alt_r: keyboard.Key.alt_l,
            keyboard.Key.alt_gr: keyboard.Key.alt_l,
        }

        return modifier_map.get(key, key)

    def _combo_matches(
        self,
        registered: frozenset,
        current: frozenset
    ) -> bool:
        """
        Check if the current key combination matches a registered hotkey.

        Args:
            registered: The registered hotkey combination.
            current: The current pressed keys.

        Returns:
            True if the combos match, False otherwise.
        """
        # All registered keys must be in current keys
        # This allows for extra modifiers but ensures base combo is matched
        return registered.issubset(current) and len(current) == len(registered)

    def _trigger_action(self, action: str) -> None:
        """
        Trigger the action associated with a hotkey.

        Uses QMetaObject.invokeMethod to safely emit signals from
        the background pynput thread to the main Qt thread.

        Args:
            action: The action name to trigger.
        """
        self._logger.info(f"Triggering hotkey action: {action}")

        if action == "capture_area":
            # Invoke on main thread using Qt's thread-safe mechanism
            QMetaObject.invokeMethod(
                self,
                "_emit_area_capture",
                Qt.ConnectionType.QueuedConnection
            )
        elif action == "capture_fullscreen":
            QMetaObject.invokeMethod(
                self,
                "_emit_fullscreen_capture",
                Qt.ConnectionType.QueuedConnection
            )

    @Slot()
    def _emit_area_capture(self) -> None:
        """Emit the area capture signal on the main thread."""
        self._logger.debug("Emitting area_capture_triggered signal")
        self.area_capture_triggered.emit()

    @Slot()
    def _emit_fullscreen_capture(self) -> None:
        """Emit the fullscreen capture signal on the main thread."""
        self._logger.debug("Emitting fullscreen_capture_triggered signal")
        self.fullscreen_capture_triggered.emit()

    def stop(self) -> None:
        """Stop the hotkey listener."""
        if self._listener:
            self._logger.debug("Stopping global hotkey listener")
            self._listener.stop()
            self._listener = None
            self._logger.info("Global hotkey listener stopped")

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.stop()
