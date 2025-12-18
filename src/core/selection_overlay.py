"""
Selection overlay for area capture in UbShot.

This module provides a fullscreen overlay widget that allows users to select
a rectangular region for screenshot capture. The workflow is:

1. Capture the entire screen(s) FIRST (before showing overlay)
2. Show the overlay with the captured image as background
3. Dim the background and let user drag-select a region
4. Crop the selected region from the pre-captured image

This approach ensures the user sees the actual screen content (frozen)
rather than the overlay itself. This mimics Shottr's area capture experience.
"""

from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QImage,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

from src.services.logging_service import get_logger


class SelectionOverlay(QWidget):
    """
    Fullscreen overlay widget for area selection.

    Displays a pre-captured screenshot with a dimmed overlay. User can
    drag-select a rectangular region. On release, crops that region
    from the pre-captured image and emits capture_completed.

    The key insight is that we FIRST capture the screen, THEN show the
    overlay. This way, the user sees a frozen snapshot of the screen
    rather than the overlay itself.

    Signals:
        capture_completed: Emitted with QImage when capture is successful.
        capture_cancelled: Emitted when user cancels (ESC key).
    """

    capture_completed = Signal(QImage)
    capture_cancelled = Signal()

    # Overlay appearance constants
    DIM_COLOR = QColor(0, 0, 0, 100)  # Semi-transparent black overlay
    SELECTION_BORDER_COLOR = QColor(80, 160, 255)  # Light blue
    SELECTION_BORDER_WIDTH = 2

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the selection overlay.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._logger = get_logger(__name__)

        # The pre-captured screenshot (full virtual desktop)
        self._background_pixmap: Optional[QPixmap] = None
        self._background_image: Optional[QImage] = None

        # Selection state
        self._selecting = False
        self._start_point: Optional[QPoint] = None
        self._current_point: Optional[QPoint] = None
        self._selection_rect: Optional[QRect] = None

        # Geometry info
        self._geometry: QRect = QRect()

        self._setup_window()

    def _setup_window(self) -> None:
        """Configure the overlay window properties."""
        # Frameless, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.BypassWindowManagerHint
        )

        # Set widget attributes
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # Set crosshair cursor for precise selection
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        # Track mouse for selection
        self.setMouseTracking(True)

        # Strong focus for keyboard input
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_screenshot(self, pixmap: QPixmap, geometry: QRect) -> None:
        """
        Set the pre-captured screenshot to display.

        Args:
            pixmap: The captured screenshot as QPixmap.
            geometry: The geometry of the virtual desktop.
        """
        self._background_pixmap = pixmap
        self._background_image = pixmap.toImage()
        self._geometry = geometry
        self._logger.debug(f"Screenshot set: {pixmap.width()}x{pixmap.height()}")

    def start_selection(self) -> None:
        """
        Start the area selection process.

        The screenshot must be set via set_screenshot() before calling this.
        """
        if not self._background_pixmap:
            self._logger.error("No screenshot set, cannot start selection!")
            self._cancel()
            return

        self._logger.debug("Starting area selection overlay")

        # Set geometry to match the screenshot
        self.setGeometry(self._geometry)

        # Reset selection state
        self._selecting = False
        self._start_point = None
        self._current_point = None
        self._selection_rect = None

        # Show fullscreen
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.setFocus()

        # Grab mouse and keyboard for reliable input
        self.grabMouse()
        self.grabKeyboard()

        self._logger.info(f"Selection overlay shown, geometry: {self._geometry}")

    def paintEvent(self, event) -> None:
        """Paint the overlay with background image and selection rectangle."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the pre-captured screenshot as background
        if self._background_pixmap:
            painter.drawPixmap(0, 0, self._background_pixmap)

        # Draw semi-transparent dim overlay on top
        painter.fillRect(self.rect(), self.DIM_COLOR)

        # If we have a selection, draw the clear (non-dimmed) selection area
        if self._selection_rect and not self._selection_rect.isNull():
            # Draw the original image in the selection area (removes dim)
            if self._background_pixmap:
                painter.drawPixmap(
                    self._selection_rect,
                    self._background_pixmap,
                    self._selection_rect
                )

            # Draw selection border
            pen = QPen(self.SELECTION_BORDER_COLOR, self.SELECTION_BORDER_WIDTH)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._selection_rect)

            # Draw selection dimensions text
            self._draw_dimensions(painter)

        painter.end()

    def _draw_dimensions(self, painter: QPainter) -> None:
        """Draw selection dimensions near the selection rectangle."""
        if not self._selection_rect:
            return

        width = abs(self._selection_rect.width())
        height = abs(self._selection_rect.height())
        dims_text = f"{width} × {height}"

        # Position text below the selection rectangle
        text_x = self._selection_rect.center().x() - 30
        text_y = self._selection_rect.bottom() + 20

        # Ensure text is within screen bounds
        if text_y > self.height() - 30:
            text_y = self._selection_rect.top() - 10

        # Draw text with shadow for visibility
        painter.setPen(QColor(0, 0, 0, 200))
        painter.drawText(text_x + 1, text_y + 1, dims_text)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(text_x, text_y, dims_text)

    def mousePressEvent(self, event) -> None:
        """Handle mouse press to start selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = True
            self._start_point = event.position().toPoint()
            self._current_point = self._start_point
            self._selection_rect = QRect(self._start_point, self._start_point)
            self.update()
            self._logger.debug(f"Selection started at {self._start_point}")

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move to update selection rectangle."""
        if self._selecting and self._start_point:
            self._current_point = event.position().toPoint()
            self._selection_rect = QRect(
                self._start_point, self._current_point
            ).normalized()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release to complete selection."""
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            self._current_point = event.position().toPoint()
            self._selection_rect = QRect(
                self._start_point, self._current_point
            ).normalized()

            self._logger.debug(f"Selection completed: {self._selection_rect}")

            # Check if selection is valid (not too small)
            if self._selection_rect.width() > 5 and self._selection_rect.height() > 5:
                self._complete_capture()
            else:
                self._logger.warning("Selection too small, cancelling")
                self._cancel()

    def keyPressEvent(self, event) -> None:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self._logger.info("Selection cancelled by ESC key")
            self._cancel()
        else:
            super().keyPressEvent(event)

    def _release_grabs(self) -> None:
        """Release mouse and keyboard grabs."""
        self.releaseMouse()
        self.releaseKeyboard()

    def _complete_capture(self) -> None:
        """Crop the selected region from the pre-captured image and emit."""
        if not self._selection_rect or not self._background_image:
            self._cancel()
            return

        # Crop the selected region from the pre-captured image
        cropped = self._background_image.copy(self._selection_rect)

        self._logger.info(
            f"Cropped image: {cropped.width()}x{cropped.height()}"
        )

        # Clean up and emit
        self._release_grabs()
        self.capture_completed.emit(cropped)
        self.close()

    def _cancel(self) -> None:
        """Cancel the selection and close overlay."""
        self._release_grabs()
        self.capture_cancelled.emit()
        self.close()

    def closeEvent(self, event) -> None:
        """Ensure grabs are released on close."""
        self._release_grabs()
        super().closeEvent(event)
