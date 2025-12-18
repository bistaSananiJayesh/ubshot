"""
Configuration service for UbShot application.

This module handles loading, saving, and managing application settings.
Configuration is stored as JSON in ~/.config/ubshot/config.json following
the XDG Base Directory Specification.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.services.logging_service import get_logger

# Default configuration directory following XDG Base Directory Specification
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "ubshot"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    "theme": "dark",
    # Screenshot save location - uses ~/Pictures/UbShot as default
    "default_save_folder": str(Path.home() / "Pictures" / "UbShot"),
    # Automatically copy screenshot to clipboard after capture
    "auto_copy_to_clipboard": True,
    # Automatically save screenshot to default folder after capture
    "auto_save": False,
    # Hotkey configurations for capture actions
    # Format: modifier keys + key, e.g., "ctrl+shift+a"
    # Note: These are global hotkeys (X11 only for now, Wayland support later)
    "hotkeys": {
        "capture_area": "ctrl+shift+a",
        "capture_fullscreen": "ctrl+shift+s",
        # TODO: Add more hotkeys in future phases:
        # "capture_window": "ctrl+shift+w",  # Phase 2
        # "capture_scrolling": "ctrl+shift+c",  # Phase 4
        # "ocr_capture": "ctrl+shift+o",  # Phase 4
    },
    # TODO: Add more settings in future phases:
    # - ocr_language: str (Phase 4+)
    # - s3_bucket: str (Phase 4+)
    # - s3_region: str (Phase 4+)
}


class ConfigService:
    """
    Service for managing application configuration.

    Handles loading, saving, and accessing configuration values.
    Provides sensible defaults when config file is missing or corrupted.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize the ConfigService.

        Args:
            config_path: Optional path to config file. Defaults to
                        ~/.config/ubshot/config.json
        """
        self._logger = get_logger(__name__)
        self._config_path = config_path or DEFAULT_CONFIG_FILE
        self._config: Dict[str, Any] = {}

        self._load()

    def _load(self) -> None:
        """Load configuration from file, using defaults if needed."""
        # Start with a deep copy of defaults
        self._config = self._deep_copy_defaults()

        if not self._config_path.exists():
            self._logger.info(
                f"Config file not found at {self._config_path}. Using defaults."
            )
            # Create the config file with defaults
            self._save_to_file()
            return

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)

            # Merge loaded config with defaults (loaded values override defaults)
            if isinstance(loaded_config, dict):
                self._deep_merge(self._config, loaded_config)
                self._logger.info(f"Configuration loaded from {self._config_path}")
                # Save back to ensure any new default keys are persisted
                self._save_to_file()
            else:
                raise ValueError("Config file does not contain a valid JSON object")

        except (json.JSONDecodeError, ValueError) as e:
            self._logger.warning(
                f"Config file corrupted or invalid: {e}. Recreating with defaults."
            )
            self._config = self._deep_copy_defaults()
            self._save_to_file()

        except (OSError, PermissionError) as e:
            self._logger.warning(
                f"Could not read config file: {e}. Using defaults."
            )

    def _deep_copy_defaults(self) -> Dict[str, Any]:
        """Create a deep copy of default config."""
        import copy
        return copy.deepcopy(DEFAULT_CONFIG)

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Recursively merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _save_to_file(self) -> None:
        """Save current configuration to file."""
        try:
            # Create config directory if it doesn't exist
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)

            self._logger.debug(f"Configuration saved to {self._config_path}")

        except (OSError, PermissionError) as e:
            self._logger.error(f"Could not save config file: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: The configuration key to retrieve.
            default: Default value if key doesn't exist.

        Returns:
            The configuration value, or default if not found.
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value (in memory only).

        Args:
            key: The configuration key to set.
            value: The value to set.

        Note:
            Call save() to persist changes to disk.
        """
        self._config[key] = value
        self._logger.debug(f"Config key '{key}' set to '{value}'")

    def save(self) -> None:
        """Persist current configuration to disk."""
        self._save_to_file()

    # ─── Theme Settings ───────────────────────────────────────────────────

    @property
    def theme(self) -> str:
        """Get the current theme setting."""
        return self.get("theme", "dark")

    # ─── Screenshot Settings ──────────────────────────────────────────────

    @property
    def default_save_folder(self) -> str:
        """Get the default save folder for screenshots."""
        return self.get("default_save_folder", str(Path.home() / "Pictures" / "UbShot"))

    @property
    def auto_copy_to_clipboard(self) -> bool:
        """Get the auto-copy-to-clipboard setting."""
        return self.get("auto_copy_to_clipboard", True)

    @property
    def auto_save(self) -> bool:
        """Get the auto-save setting."""
        return self.get("auto_save", False)

    # ─── Hotkey Settings ──────────────────────────────────────────────────

    @property
    def hotkeys(self) -> Dict[str, str]:
        """Get all hotkey configurations."""
        return self.get("hotkeys", DEFAULT_CONFIG["hotkeys"])

    @property
    def hotkey_capture_area(self) -> str:
        """Get the hotkey for area capture."""
        hotkeys = self.hotkeys
        return hotkeys.get("capture_area", "ctrl+shift+a")

    @property
    def hotkey_capture_fullscreen(self) -> str:
        """Get the hotkey for fullscreen capture."""
        hotkeys = self.hotkeys
        return hotkeys.get("capture_fullscreen", "ctrl+shift+s")
