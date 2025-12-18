"""
System tray service for UbShot application.

This module provides system tray integration including:
- Tray icon with context menu
- Quick access to capture actions
- Application preferences and quit options

The tray menu mimics Shottr's tray behavior for familiarity.
"""

from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

from src.services.logging_service import get_logger


class TrayService(QObject):
    """
    System tray icon and menu service.

    Provides a system tray icon with context menu for:
    - Capture Area
    - Capture Fullscreen
    - Preferences
    - Quit

    Signals:
        capture_area_requested: Emitted when user clicks "Capture Area".
        capture_fullscreen_requested: Emitted when user clicks "Capture Fullscreen".
        preferences_requested: Emitted when user clicks "Preferences".
        quit_requested: Emitted when user clicks "Quit".
    """

    capture_area_requested = Signal()
    capture_fullscreen_requested = Signal()
    preferences_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """
        Initialize the tray service.

        Args:
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._logger = get_logger(__name__)

        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._tray_menu: Optional[QMenu] = None

        self._setup_tray()

    def _setup_tray(self) -> None:
        """Set up the system tray icon and menu."""
        # Create tray icon
        self._tray_icon = QSystemTrayIcon(self._create_icon(), None)
        self._tray_icon.setToolTip("UbShot - Screenshot Tool")

        # Create context menu
        self._tray_menu = QMenu()
        self._setup_menu()

        self._tray_icon.setContextMenu(self._tray_menu)

        # Connect double-click to show preferences (or main window in future)
        self._tray_icon.activated.connect(self._on_tray_activated)

        self._logger.info("Tray service initialized")

    def _create_icon(self) -> QIcon:
        """
        Create a simple camera-like icon for the tray.

        Returns a programmatically drawn icon since we're not using
        external resources in this phase. The icon is a simple camera
        silhouette in a contrasting color.
        """
        # Create a 64x64 pixmap with transparent background
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw a simple camera shape with white color for visibility
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QColor(255, 255, 255))

        # Camera body
        painter.drawRoundedRect(8, 20, 48, 32, 4, 4)

        # Camera lens (circle) - darker
        painter.setBrush(QColor(60, 60, 60))
        painter.drawEllipse(22, 24, 20, 20)

        # Camera flash/viewfinder
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRect(12, 14, 12, 8)

        painter.end()

        return QIcon(pixmap)

    def _setup_menu(self) -> None:
        """Set up the tray context menu actions."""
        if not self._tray_menu:
            return

        # ─── Capture Actions ──────────────────────────────────────────
        capture_area_action = QAction("Capture Area", self._tray_menu)
        capture_area_action.setStatusTip("Capture a selected region (Ctrl+Shift+A)")
        # Use lambda to avoid triggered(bool) signature issue
        capture_area_action.triggered.connect(lambda checked=False: self._on_capture_area())
        self._tray_menu.addAction(capture_area_action)

        capture_fullscreen_action = QAction("Capture Fullscreen", self._tray_menu)
        capture_fullscreen_action.setStatusTip("Capture the entire screen (Ctrl+Shift+S)")
        capture_fullscreen_action.triggered.connect(lambda checked=False: self._on_capture_fullscreen())
        self._tray_menu.addAction(capture_fullscreen_action)

        # TODO: Add more capture options in future phases:
        # - Capture Window (Phase 2)
        # - Capture Scrolling (Phase 4)

        self._tray_menu.addSeparator()

        # ─── Application Actions ──────────────────────────────────────
        # TODO: Add "Open Editor" action when we have a proper editor (Phase 2)
        # TODO: Add "Recent Screenshots" submenu (Phase 2)

        preferences_action = QAction("Preferences...", self._tray_menu)
        preferences_action.triggered.connect(lambda checked=False: self._on_preferences())
        self._tray_menu.addAction(preferences_action)

        self._tray_menu.addSeparator()

        quit_action = QAction("Quit", self._tray_menu)
        quit_action.triggered.connect(lambda checked=False: self._on_quit())
        self._tray_menu.addAction(quit_action)

    def show(self) -> None:
        """Show the tray icon."""
        if self._tray_icon:
            self._tray_icon.show()
            self._logger.debug("Tray icon shown")

    def hide(self) -> None:
        """Hide the tray icon."""
        if self._tray_icon:
            self._tray_icon.hide()
            self._logger.debug("Tray icon hidden")

    def show_message(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        duration_ms: int = 3000
    ) -> None:
        """
        Show a notification message from the tray.

        Args:
            title: The notification title.
            message: The notification message.
            icon: The icon type (Information, Warning, Critical, NoIcon).
            duration_ms: Duration to show the message in milliseconds.
        """
        if self._tray_icon:
            self._tray_icon.showMessage(title, message, icon, duration_ms)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (click, double-click, etc.)."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._logger.debug("Tray icon double-clicked")
            # TODO: Show main window or last screenshot in Phase 2
            self.preferences_requested.emit()

    def _on_capture_area(self) -> None:
        """Handle Capture Area menu action."""
        self._logger.info("Capture Area requested from tray")
        # Use timer to let menu close before starting capture
        QTimer.singleShot(150, self.capture_area_requested.emit)

    def _on_capture_fullscreen(self) -> None:
        """Handle Capture Fullscreen menu action."""
        self._logger.info("Capture Fullscreen requested from tray")
        # Use timer to let menu close before starting capture
        QTimer.singleShot(150, self.capture_fullscreen_requested.emit)

    def _on_preferences(self) -> None:
        """Handle Preferences menu action."""
        self._logger.info("Preferences requested from tray")
        # For now, show a simple info dialog
        # TODO: Replace with proper preferences window in Phase 2
        QMessageBox.information(
            None,
            "UbShot Preferences",
            "Preferences dialog will be implemented in a future phase.\n\n"
            "Current settings are stored in:\n"
            "~/.config/ubshot/config.json"
        )
        self.preferences_requested.emit()

    def _on_quit(self) -> None:
        """Handle Quit menu action."""
        self._logger.info("Quit requested from tray")
        self.quit_requested.emit()
