"""
Capture service for UbShot application.

This module handles all screenshot capture logic including:
- Area capture with selection overlay
- Fullscreen capture
- Multi-monitor support

The capture flow for area capture:
1. Capture the entire virtual desktop FIRST (before any overlay)
2. Show the selection overlay with the captured image as background
3. User selects a region on the frozen screenshot
4. Crop the selected region from the pre-captured image

This approach ensures users see the actual screen content, not the overlay.
"""

from typing import Optional

from PySide6.QtCore import QObject, QPoint, QRect, QTimer, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QImage, QPixmap, QScreen

from src.core.selection_overlay import SelectionOverlay
from src.services.logging_service import get_logger


class CaptureService(QObject):
    """
    Service for capturing screenshots.

    Provides methods for area and fullscreen capture with proper
    multi-monitor support. Emits signals when capture is complete
    or cancelled.

    Signals:
        capture_completed: Emitted with QImage when capture succeeds.
        capture_cancelled: Emitted when user cancels capture.
    """

    capture_completed = Signal(QImage)
    capture_cancelled = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """
        Initialize the capture service.

        Args:
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._logger = get_logger(__name__)
        self._selection_overlay: Optional[SelectionOverlay] = None

    def start_area_capture(self) -> None:
        """
        Start an area capture session.

        The flow is:
        1. Capture the entire virtual desktop immediately
        2. Show a fullscreen overlay with the captured image
        3. User drags to select a region
        4. On release, crop the region from the pre-captured image

        This ensures the user sees the actual screen, not the overlay.
        """
        self._logger.info("Starting area capture")

        # Step 1: Capture the entire virtual desktop FIRST
        primary_screen = QGuiApplication.primaryScreen()
        if not primary_screen:
            self._logger.error("No primary screen available!")
            self.capture_cancelled.emit()
            return

        # Get virtual geometry (all screens combined)
        virtual_geo = primary_screen.virtualGeometry()
        self._logger.debug(f"Virtual desktop geometry: {virtual_geo}")

        # Capture the entire virtual desktop
        # We need to combine all screens into one image
        full_screenshot = self._capture_virtual_desktop(virtual_geo)

        if full_screenshot.isNull():
            self._logger.error("Failed to capture virtual desktop!")
            self.capture_cancelled.emit()
            return

        self._logger.debug(
            f"Captured virtual desktop: {full_screenshot.width()}x{full_screenshot.height()}"
        )

        # Step 2: Create and show the selection overlay
        self._selection_overlay = SelectionOverlay()
        self._selection_overlay.set_screenshot(full_screenshot, virtual_geo)

        # Connect overlay signals
        self._selection_overlay.capture_completed.connect(self._on_capture_completed)
        self._selection_overlay.capture_cancelled.connect(self._on_capture_cancelled)

        # Step 3: Start the selection process
        self._selection_overlay.start_selection()

    def _capture_virtual_desktop(self, virtual_geo: QRect) -> QPixmap:
        """
        Capture the entire virtual desktop (all screens).

        Args:
            virtual_geo: The geometry of the virtual desktop.

        Returns:
            A QPixmap containing the combined screenshot of all screens.
        """
        # Create a pixmap to hold the entire virtual desktop
        result = QPixmap(virtual_geo.size())
        result.fill()  # Fill with default color

        from PySide6.QtGui import QPainter
        painter = QPainter(result)

        # Capture each screen and paint it at the correct position
        for screen in QGuiApplication.screens():
            screen_geo = screen.geometry()
            self._logger.debug(f"Capturing screen {screen.name()}: {screen_geo}")

            # Capture this screen
            screen_pixmap = screen.grabWindow(0)

            # Calculate position relative to virtual desktop origin
            x = screen_geo.x() - virtual_geo.x()
            y = screen_geo.y() - virtual_geo.y()

            # Paint this screen's capture at the correct position
            painter.drawPixmap(x, y, screen_pixmap)

        painter.end()
        return result

    def capture_fullscreen(self) -> None:
        """
        Capture the entire screen where the cursor is located.

        Detects which screen contains the mouse cursor and captures
        that screen. Falls back to primary screen if detection fails.

        The captured image is emitted via capture_completed signal.
        """
        self._logger.info("Starting fullscreen capture")

        # Small delay to allow any UI elements to settle
        # (e.g., if triggered from a menu that needs to close)
        QTimer.singleShot(200, self._do_fullscreen_capture)

    def _do_fullscreen_capture(self) -> None:
        """Perform the actual fullscreen capture."""
        # Get current cursor position to determine which screen to capture
        cursor_pos: QPoint = QCursor.pos()
        self._logger.debug(f"Cursor position: {cursor_pos}")

        # Find the screen containing the cursor
        target_screen: Optional[QScreen] = None
        for screen in QGuiApplication.screens():
            if screen.geometry().contains(cursor_pos):
                target_screen = screen
                self._logger.debug(f"Cursor is on screen: {screen.name()}")
                break

        # Fallback to primary screen if cursor screen not found
        if target_screen is None:
            target_screen = QGuiApplication.primaryScreen()
            if target_screen:
                self._logger.warning(
                    f"Could not find cursor screen, using primary: {target_screen.name()}"
                )
            else:
                self._logger.error("No screen available for capture!")
                self.capture_cancelled.emit()
                return

        # Capture the entire screen
        # grabWindow(0) captures the entire screen, not a specific window
        pixmap = target_screen.grabWindow(0)
        image = pixmap.toImage()

        self._logger.info(
            f"Fullscreen captured: {image.width()}x{image.height()} from {target_screen.name()}"
        )

        self.capture_completed.emit(image)

    def _on_capture_completed(self, image: QImage) -> None:
        """Handle successful capture from overlay."""
        self._logger.debug("Capture completed from overlay")
        self._cleanup_overlay()
        self.capture_completed.emit(image)

    def _on_capture_cancelled(self) -> None:
        """Handle capture cancellation from overlay."""
        self._logger.debug("Capture cancelled by user")
        self._cleanup_overlay()
        self.capture_cancelled.emit()

    def _cleanup_overlay(self) -> None:
        """Clean up the selection overlay."""
        if self._selection_overlay:
            self._selection_overlay.deleteLater()
            self._selection_overlay = None
