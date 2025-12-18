"""
Editor placeholder widget for UbShot application.

This module contains a placeholder widget that displays captured screenshots.
In Phase 2+, this will be replaced by a full annotation editor canvas with
drawing tools, shapes, text, blur, etc.

For Phase 1, this widget simply displays the captured image scaled to fit,
or a placeholder message when no image is loaded.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from src.services.logging_service import get_logger


class EditorPlaceholder(QWidget):
    """
    Placeholder widget for the editor canvas area.

    Displays captured screenshots scaled to fit the widget, or a placeholder
    message when no screenshot is loaded.

    TODO: Replace this placeholder with the real editor canvas in Phase 2+.
    The real editor will include:
    - Screenshot display canvas with pan/zoom
    - Annotation tools (arrows, shapes, text, blur, etc.)
    - Undo/redo support
    - Layer management
    - Export options
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the EditorPlaceholder widget.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._logger = get_logger(__name__)

        # The current image being displayed
        self._image: Optional[QImage] = None
        self._scaled_pixmap: Optional[QPixmap] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the placeholder UI."""
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Set dark background
        self.setStyleSheet("background-color: #232323;")

    def set_image(self, image: QImage) -> None:
        """
        Set the image to display.

        Args:
            image: The QImage to display.
        """
        self._image = image
        self._update_scaled_pixmap()
        self.update()  # Trigger repaint

        self._logger.info(
            f"Editor placeholder: image set ({image.width()}x{image.height()})"
        )

    def clear_image(self) -> None:
        """Clear the current image."""
        self._image = None
        self._scaled_pixmap = None
        self.update()
        self._logger.debug("Editor placeholder: image cleared")

    def has_image(self) -> bool:
        """Check if an image is currently loaded."""
        return self._image is not None

    def get_image(self) -> Optional[QImage]:
        """Get the current image."""
        return self._image

    def _update_scaled_pixmap(self) -> None:
        """Update the scaled pixmap for display."""
        if self._image is None:
            self._scaled_pixmap = None
            return

        # Scale image to fit widget while maintaining aspect ratio
        widget_size = self.size()
        pixmap = QPixmap.fromImage(self._image)

        self._scaled_pixmap = pixmap.scaled(
            widget_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    def resizeEvent(self, event) -> None:
        """Handle widget resize to rescale the image."""
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def paintEvent(self, event) -> None:
        """Paint the widget with image or placeholder."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill background
        painter.fillRect(self.rect(), self.palette().window().color())

        if self._scaled_pixmap and not self._scaled_pixmap.isNull():
            # Draw the image centered
            x = (self.width() - self._scaled_pixmap.width()) // 2
            y = (self.height() - self._scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, self._scaled_pixmap)

            # Draw image dimensions at bottom
            self._draw_image_info(painter)
        else:
            # Draw placeholder text
            self._draw_placeholder(painter)

        painter.end()

    def _draw_placeholder(self, painter: QPainter) -> None:
        """Draw placeholder text when no image is loaded."""
        # Main message
        font = QFont()
        font.setPointSize(16)
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.gray)

        main_text = "No screenshot yet"
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            main_text
        )

        # Hint text below
        font.setPointSize(11)
        painter.setFont(font)
        painter.setPen(Qt.GlobalColor.darkGray)

        hint_rect = self.rect().adjusted(0, 40, 0, 0)
        hint_text = (
            "Use the tray menu or press:\n"
            "Ctrl+Shift+A for area capture\n"
            "Ctrl+Shift+S for fullscreen capture"
        )
        painter.drawText(
            hint_rect,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            hint_text
        )

    def _draw_image_info(self, painter: QPainter) -> None:
        """Draw image information overlay."""
        if not self._image:
            return

        # Draw info at bottom of widget
        info_text = f"{self._image.width()} × {self._image.height()} px"

        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)

        # Draw with semi-transparent background
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(info_text)
        text_height = metrics.height()

        padding = 8
        bg_rect = self.rect().adjusted(
            (self.width() - text_width) // 2 - padding,
            self.height() - text_height - padding * 3,
            -(self.width() - text_width) // 2 + padding,
            -padding
        )

        painter.fillRect(bg_rect, Qt.GlobalColor.black)
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(
            bg_rect,
            Qt.AlignmentFlag.AlignCenter,
            info_text
        )
