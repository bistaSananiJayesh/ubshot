"""
Annotation models for UbShot editor.

This module provides the data models for all annotation types that can be
drawn on the canvas. Each annotation knows how to:
- Paint itself on a QPainter
- Hit-test for selection
- Move and resize
- Serialize its properties

Annotation Types:
- RectangleAnnotation: Outlined/filled rectangle
- EllipseAnnotation: Outlined/filled ellipse
- ArrowAnnotation: Line with arrowhead
- TextAnnotation: Editable text box
- FreehandAnnotation: Freehand drawing path (Phase 3)
- HighlightAnnotation: Semi-transparent marker strokes (Phase 3)
- SpotlightAnnotation: Darken outside, bright inside (Phase 3)
- BlurRegionAnnotation: Pixelate/blur region (Phase 3)
- StepAnnotation: Numbered circle badge (Phase 3)
- RulerAnnotation: Distance measurement line (Phase 3)

TODO (Future Phases):
- BendableArrowAnnotation
- MagnifierAnnotation
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple
from uuid import uuid4

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QTransform,
)


class AnnotationType(Enum):
    """Enum for annotation types."""
    RECTANGLE = auto()
    ELLIPSE = auto()
    ARROW = auto()
    TEXT = auto()
    # Phase 3 annotation types
    FREEHAND = auto()
    HIGHLIGHT = auto()
    SPOTLIGHT = auto()
    BLUR_REGION = auto()
    STEP = auto()
    RULER = auto()
    INPAINT = auto()  # Content-aware eraser


@dataclass
class AnnotationStyle:
    """
    Style properties for annotations.
    
    Shared across annotation types where applicable.
    """
    stroke_color: QColor = field(default_factory=lambda: QColor(255, 80, 80))
    stroke_width: int = 3
    fill_color: Optional[QColor] = None
    opacity: float = 1.0  # 0.0 to 1.0
    font_size: int = 18
    font_bold: bool = False
    arrowhead_size: int = 12
    
    def clone(self) -> "AnnotationStyle":
        """Create a copy of this style."""
        return AnnotationStyle(
            stroke_color=QColor(self.stroke_color),
            stroke_width=self.stroke_width,
            fill_color=QColor(self.fill_color) if self.fill_color else None,
            opacity=self.opacity,
            font_size=self.font_size,
            font_bold=self.font_bold,
            arrowhead_size=self.arrowhead_size,
        )


class AnnotationBase(ABC):
    """
    Base class for all annotations.
    
    Provides common functionality for selection, hit-testing,
    painting, and transformation.
    """
    
    def __init__(self, style: Optional[AnnotationStyle] = None) -> None:
        """
        Initialize the annotation.
        
        Args:
            style: The style to use, or None for defaults.
        """
        self.id: str = str(uuid4())
        self.style: AnnotationStyle = style or AnnotationStyle()
        self.selected: bool = False
        self.z_index: int = 0  # For layering (higher = on top)
    
    @property
    @abstractmethod
    def annotation_type(self) -> AnnotationType:
        """Return the type of this annotation."""
        pass
    
    @property
    @abstractmethod
    def bounding_rect(self) -> QRectF:
        """Return the bounding rectangle of this annotation."""
        pass
    
    @abstractmethod
    def paint(self, painter: QPainter) -> None:
        """
        Paint the annotation.
        
        Args:
            painter: The QPainter to use (already transformed for zoom/pan).
        """
        pass
    
    @abstractmethod
    def hit_test(self, point: QPointF) -> bool:
        """
        Test if a point hits this annotation.
        
        Args:
            point: The point to test (in image coordinates).
            
        Returns:
            True if the point hits the annotation.
        """
        pass
    
    @abstractmethod
    def move_by(self, dx: float, dy: float) -> None:
        """
        Move the annotation by the given delta.
        
        Args:
            dx: Delta X in image coordinates.
            dy: Delta Y in image coordinates.
        """
        pass
    
    @abstractmethod
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        """
        Resize the annotation by moving a handle.
        
        Args:
            handle_index: The index of the handle (0-7 for corners/edges).
            new_pos: The new position of the handle.
        """
        pass
    
    @abstractmethod
    def clone(self) -> "AnnotationBase":
        """Create a deep copy of this annotation."""
        pass
    
    def get_resize_handles(self) -> List[QRectF]:
        """
        Get the resize handle rectangles.
        
        Returns 8 handles: 4 corners + 4 edges.
        Order: TL, TC, TR, ML, MR, BL, BC, BR
        """
        rect = self.bounding_rect
        handle_size = 8
        half = handle_size / 2
        
        handles = [
            # Top row
            QRectF(rect.left() - half, rect.top() - half, handle_size, handle_size),  # TL
            QRectF(rect.center().x() - half, rect.top() - half, handle_size, handle_size),  # TC
            QRectF(rect.right() - half, rect.top() - half, handle_size, handle_size),  # TR
            # Middle row
            QRectF(rect.left() - half, rect.center().y() - half, handle_size, handle_size),  # ML
            QRectF(rect.right() - half, rect.center().y() - half, handle_size, handle_size),  # MR
            # Bottom row
            QRectF(rect.left() - half, rect.bottom() - half, handle_size, handle_size),  # BL
            QRectF(rect.center().x() - half, rect.bottom() - half, handle_size, handle_size),  # BC
            QRectF(rect.right() - half, rect.bottom() - half, handle_size, handle_size),  # BR
        ]
        return handles
    
    def hit_test_handle(self, point: QPointF) -> int:
        """
        Test if a point hits a resize handle.
        
        Args:
            point: The point to test.
            
        Returns:
            Handle index (0-7) if hit, -1 otherwise.
        """
        handles = self.get_resize_handles()
        for i, handle in enumerate(handles):
            if handle.contains(point):
                return i
        return -1
    
    def _apply_style_to_pen(self, painter: QPainter) -> None:
        """Apply the annotation style to the painter's pen."""
        pen = QPen(self.style.stroke_color)
        pen.setWidth(self.style.stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setOpacity(self.style.opacity)


class RectangleAnnotation(AnnotationBase):
    """
    Rectangle annotation with optional fill.
    """
    
    def __init__(
        self,
        rect: QRectF,
        style: Optional[AnnotationStyle] = None
    ) -> None:
        super().__init__(style)
        self._rect = rect.normalized()
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.RECTANGLE
    
    @property
    def bounding_rect(self) -> QRectF:
        return self._rect
    
    @bounding_rect.setter
    def bounding_rect(self, rect: QRectF) -> None:
        self._rect = rect.normalized()
    
    def paint(self, painter: QPainter) -> None:
        self._apply_style_to_pen(painter)
        
        # Fill if fill color is set
        if self.style.fill_color:
            painter.setBrush(self.style.fill_color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        
        painter.drawRect(self._rect)
    
    def hit_test(self, point: QPointF) -> bool:
        # Hit test on the border (with some tolerance)
        tolerance = max(self.style.stroke_width, 5)
        outer = self._rect.adjusted(-tolerance, -tolerance, tolerance, tolerance)
        inner = self._rect.adjusted(tolerance, tolerance, -tolerance, -tolerance)
        
        # If filled, hit anywhere inside
        if self.style.fill_color:
            return outer.contains(point)
        
        # If not filled, only hit on border
        return outer.contains(point) and not inner.contains(point)
    
    def move_by(self, dx: float, dy: float) -> None:
        self._rect.translate(dx, dy)
    
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        """Resize based on which handle is being dragged."""
        rect = self._rect
        
        if handle_index == 0:  # TL
            rect.setTopLeft(new_pos)
        elif handle_index == 1:  # TC
            rect.setTop(new_pos.y())
        elif handle_index == 2:  # TR
            rect.setTopRight(new_pos)
        elif handle_index == 3:  # ML
            rect.setLeft(new_pos.x())
        elif handle_index == 4:  # MR
            rect.setRight(new_pos.x())
        elif handle_index == 5:  # BL
            rect.setBottomLeft(new_pos)
        elif handle_index == 6:  # BC
            rect.setBottom(new_pos.y())
        elif handle_index == 7:  # BR
            rect.setBottomRight(new_pos)
        
        self._rect = rect.normalized()
    
    def clone(self) -> "RectangleAnnotation":
        cloned = RectangleAnnotation(QRectF(self._rect), self.style.clone())
        cloned.z_index = self.z_index
        return cloned


class EllipseAnnotation(AnnotationBase):
    """
    Ellipse/oval annotation with optional fill.
    """
    
    def __init__(
        self,
        rect: QRectF,
        style: Optional[AnnotationStyle] = None
    ) -> None:
        super().__init__(style)
        self._rect = rect.normalized()
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.ELLIPSE
    
    @property
    def bounding_rect(self) -> QRectF:
        return self._rect
    
    @bounding_rect.setter
    def bounding_rect(self, rect: QRectF) -> None:
        self._rect = rect.normalized()
    
    def paint(self, painter: QPainter) -> None:
        self._apply_style_to_pen(painter)
        
        if self.style.fill_color:
            painter.setBrush(self.style.fill_color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        
        painter.drawEllipse(self._rect)
    
    def hit_test(self, point: QPointF) -> bool:
        # Use ellipse equation for hit testing
        center = self._rect.center()
        a = self._rect.width() / 2
        b = self._rect.height() / 2
        
        if a == 0 or b == 0:
            return False
        
        # Normalized distance from center
        dx = (point.x() - center.x()) / a
        dy = (point.y() - center.y()) / b
        dist = dx * dx + dy * dy
        
        tolerance = max(self.style.stroke_width, 5) / min(a, b) if min(a, b) > 0 else 0.2
        
        if self.style.fill_color:
            return dist <= 1 + tolerance
        else:
            return abs(dist - 1) <= tolerance
    
    def move_by(self, dx: float, dy: float) -> None:
        self._rect.translate(dx, dy)
    
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        rect = self._rect
        
        if handle_index == 0:  # TL
            rect.setTopLeft(new_pos)
        elif handle_index == 1:  # TC
            rect.setTop(new_pos.y())
        elif handle_index == 2:  # TR
            rect.setTopRight(new_pos)
        elif handle_index == 3:  # ML
            rect.setLeft(new_pos.x())
        elif handle_index == 4:  # MR
            rect.setRight(new_pos.x())
        elif handle_index == 5:  # BL
            rect.setBottomLeft(new_pos)
        elif handle_index == 6:  # BC
            rect.setBottom(new_pos.y())
        elif handle_index == 7:  # BR
            rect.setBottomRight(new_pos)
        
        self._rect = rect.normalized()
    
    def clone(self) -> "EllipseAnnotation":
        cloned = EllipseAnnotation(QRectF(self._rect), self.style.clone())
        cloned.z_index = self.z_index
        return cloned


class ArrowAnnotation(AnnotationBase):
    """
    Arrow annotation with line and arrowhead.
    """
    
    def __init__(
        self,
        start: QPointF,
        end: QPointF,
        style: Optional[AnnotationStyle] = None
    ) -> None:
        super().__init__(style)
        self._start = start
        self._end = end
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.ARROW
    
    @property
    def start(self) -> QPointF:
        return self._start
    
    @start.setter
    def start(self, point: QPointF) -> None:
        self._start = point
    
    @property
    def end(self) -> QPointF:
        return self._end
    
    @end.setter
    def end(self, point: QPointF) -> None:
        self._end = point
    
    @property
    def bounding_rect(self) -> QRectF:
        # Include arrowhead in bounds
        padding = self.style.arrowhead_size + self.style.stroke_width
        left = min(self._start.x(), self._end.x()) - padding
        top = min(self._start.y(), self._end.y()) - padding
        right = max(self._start.x(), self._end.x()) + padding
        bottom = max(self._start.y(), self._end.y()) + padding
        return QRectF(left, top, right - left, bottom - top)
    
    def paint(self, painter: QPainter) -> None:
        self._apply_style_to_pen(painter)
        painter.setBrush(self.style.stroke_color)
        
        # Draw line
        painter.drawLine(self._start, self._end)
        
        # Draw arrowhead
        self._draw_arrowhead(painter)
    
    def _draw_arrowhead(self, painter: QPainter) -> None:
        """Draw the arrowhead at the end point."""
        dx = self._end.x() - self._start.x()
        dy = self._end.y() - self._start.y()
        length = math.sqrt(dx * dx + dy * dy)
        
        if length < 1:
            return
        
        # Normalize direction
        dx /= length
        dy /= length
        
        # Arrowhead size
        size = self.style.arrowhead_size
        
        # Calculate arrowhead points
        # Perpendicular vector
        px, py = -dy, dx
        
        # Arrowhead vertices
        tip = self._end
        left = QPointF(
            tip.x() - size * dx + size * 0.5 * px,
            tip.y() - size * dy + size * 0.5 * py
        )
        right = QPointF(
            tip.x() - size * dx - size * 0.5 * px,
            tip.y() - size * dy - size * 0.5 * py
        )
        
        # Draw filled triangle
        arrowhead = QPolygonF([tip, left, right])
        painter.drawPolygon(arrowhead)
    
    def hit_test(self, point: QPointF) -> bool:
        # Distance from point to line segment
        tolerance = max(self.style.stroke_width, 8)
        
        # Vector from start to end
        dx = self._end.x() - self._start.x()
        dy = self._end.y() - self._start.y()
        length_sq = dx * dx + dy * dy
        
        if length_sq < 1:
            # Very short arrow, just check distance to start
            dist = math.sqrt(
                (point.x() - self._start.x()) ** 2 +
                (point.y() - self._start.y()) ** 2
            )
            return dist <= tolerance
        
        # Parameter t for closest point on line
        t = max(0, min(1, (
            (point.x() - self._start.x()) * dx +
            (point.y() - self._start.y()) * dy
        ) / length_sq))
        
        # Closest point
        closest_x = self._start.x() + t * dx
        closest_y = self._start.y() + t * dy
        
        dist = math.sqrt(
            (point.x() - closest_x) ** 2 +
            (point.y() - closest_y) ** 2
        )
        return dist <= tolerance
    
    def move_by(self, dx: float, dy: float) -> None:
        self._start = QPointF(self._start.x() + dx, self._start.y() + dy)
        self._end = QPointF(self._end.x() + dx, self._end.y() + dy)
    
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        # For arrows, we use handles 0 (start) and 7 (end)
        if handle_index in (0, 1, 3, 5):  # Left side handles -> move start
            self._start = new_pos
        else:  # Right side handles -> move end
            self._end = new_pos
    
    def get_resize_handles(self) -> List[QRectF]:
        """Arrow only has 2 handles: start and end."""
        handle_size = 8
        half = handle_size / 2
        
        return [
            QRectF(self._start.x() - half, self._start.y() - half, handle_size, handle_size),
            QRectF(self._end.x() - half, self._end.y() - half, handle_size, handle_size),
        ]
    
    def hit_test_handle(self, point: QPointF) -> int:
        handles = self.get_resize_handles()
        for i, handle in enumerate(handles):
            if handle.contains(point):
                # Return 0 for start, 7 for end (to match resize logic)
                return 0 if i == 0 else 7
        return -1
    
    def clone(self) -> "ArrowAnnotation":
        cloned = ArrowAnnotation(
            QPointF(self._start), QPointF(self._end), self.style.clone()
        )
        cloned.z_index = self.z_index
        return cloned


class TextAnnotation(AnnotationBase):
    """
    Shottr-like text annotation with thought bubble and pointer spike.
    
    Features:
    - Rounded rectangle background bubble with shadow
    - Movable triangular spike/pointer to reference content
    - Hand-drawn wobbly style (toggle with Ctrl+R)
    - Auto text color contrast (light bg → black, dark bg → white)
    - Auto sizing based on font
    """
    
    def __init__(
        self,
        position: QPointF,
        text: str = "Text",
        style: Optional[AnnotationStyle] = None
    ) -> None:
        super().__init__(style)
        self._position = position
        self._text = text
        self._cached_rect: Optional[QRectF] = None
        
        # Shottr-like features
        self.show_bubble: bool = True  # Show background bubble
        self.bubble_color: QColor = QColor(211, 78, 78)  # Red (#D34E4E) like Shottr
        self.bubble_radius: int = 8  # Corner radius
        self.bubble_padding: int = 12  # Padding around text
        
        # Spike/pointer
        self.spike_enabled: bool = True
        self.spike_offset: QPointF = QPointF(0, 30)  # Offset from bubble bottom
        self._spike_size: int = 15  # Size of spike triangle
        
        # Hand-drawn style
        self.hand_drawn: bool = False
        self.hand_drawn_seed: int = 42  # Randomization seed
        
        # Shadow
        self.show_shadow: bool = True
        self.shadow_offset: int = 3
        self.shadow_blur: int = 5
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.TEXT
    
    @property
    def text(self) -> str:
        return self._text
    
    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        self._cached_rect = None
    
    @property
    def position(self) -> QPointF:
        return self._position
    
    @position.setter
    def position(self, pos: QPointF) -> None:
        self._position = pos
        self._cached_rect = None
    
    @property
    def bounding_rect(self) -> QRectF:
        if self._cached_rect is None:
            self._cached_rect = self._calculate_bounding_rect()
        return self._cached_rect
    
    @property
    def bubble_rect(self) -> QRectF:
        """Get the rectangle of just the bubble (without spike)."""
        return self._calculate_bubble_rect()
    
    @property
    def spike_tip(self) -> QPointF:
        """Get the position of the spike tip."""
        bubble = self.bubble_rect
        return QPointF(
            bubble.center().x() + self.spike_offset.x(),
            bubble.bottom() + self.spike_offset.y()
        )
    
    def _calculate_bubble_rect(self) -> QRectF:
        """Calculate the bubble rectangle based on text and font."""
        font = self._get_font()
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        
        # Handle multi-line text
        lines = self._text.split('\n') if self._text else ['']
        max_width = max(metrics.horizontalAdvance(line) for line in lines)
        total_height = metrics.height() * len(lines)
        
        # Minimum size for empty text (so cursor is visible)
        min_width = 60
        min_height = metrics.height()
        
        padding = self.bubble_padding
        return QRectF(
            self._position.x() - padding,
            self._position.y() - metrics.ascent() - padding,
            max(max_width, min_width) + padding * 2,
            max(total_height, min_height) + padding * 2
        )
    
    def _calculate_bounding_rect(self) -> QRectF:
        """Calculate full bounding rect including spike."""
        bubble = self._calculate_bubble_rect()
        
        if self.spike_enabled:
            spike_tip = self.spike_tip
            # Extend rect to include spike
            return bubble.united(QRectF(
                spike_tip.x() - 5, spike_tip.y() - 5, 10, 10
            ))
        
        return bubble
    
    def _get_font(self) -> QFont:
        """Get the font for this text annotation."""
        font = QFont()
        font.setPixelSize(self.style.font_size)
        font.setBold(self.style.font_bold)
        return font
    
    def _get_contrasting_text_color(self) -> QColor:
        """Calculate text color based on bubble background luminance."""
        if not self.show_bubble:
            return self.style.stroke_color
        
        # Calculate luminance of bubble color
        r, g, b = self.bubble_color.red(), self.bubble_color.green(), self.bubble_color.blue()
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        
        # Use black text on light backgrounds, white on dark
        return QColor(0, 0, 0) if luminance > 0.5 else QColor(255, 255, 255)
    
    def _wobble_point(self, point: QPointF, seed_offset: int = 0) -> QPointF:
        """Apply hand-drawn wobble to a point."""
        if not self.hand_drawn:
            return point
        
        import random
        random.seed(self.hand_drawn_seed + seed_offset)
        wobble = 2.0
        return QPointF(
            point.x() + random.uniform(-wobble, wobble),
            point.y() + random.uniform(-wobble, wobble)
        )
    
    def _create_bubble_path(self, rect: QRectF) -> QPainterPath:
        """Create the bubble path with optional hand-drawn wobble."""
        path = QPainterPath()
        r = self.bubble_radius
        
        if self.hand_drawn:
            # Hand-drawn style - wobbly rounded rect
            steps = 20
            points = []
            
            # Top edge
            for i in range(steps):
                t = i / steps
                x = rect.left() + r + t * (rect.width() - 2 * r)
                points.append(self._wobble_point(QPointF(x, rect.top()), i))
            
            # Right edge
            for i in range(steps):
                t = i / steps
                y = rect.top() + r + t * (rect.height() - 2 * r)
                points.append(self._wobble_point(QPointF(rect.right(), y), steps + i))
            
            # Bottom edge
            for i in range(steps):
                t = i / steps
                x = rect.right() - r - t * (rect.width() - 2 * r)
                points.append(self._wobble_point(QPointF(x, rect.bottom()), 2 * steps + i))
            
            # Left edge
            for i in range(steps):
                t = i / steps
                y = rect.bottom() - r - t * (rect.height() - 2 * r)
                points.append(self._wobble_point(QPointF(rect.left(), y), 3 * steps + i))
            
            if points:
                path.moveTo(points[0])
                for p in points[1:]:
                    path.lineTo(p)
                path.closeSubpath()
        else:
            # Clean rounded rectangle
            path.addRoundedRect(rect, r, r)
        
        return path
    
    def paint(self, painter: QPainter) -> None:
        painter.save()
        painter.setOpacity(self.style.opacity)
        
        bubble = self.bubble_rect
        
        if self.show_bubble:
            # Draw shadow
            if self.show_shadow:
                shadow_rect = bubble.translated(self.shadow_offset, self.shadow_offset)
                shadow_path = self._create_bubble_path(shadow_rect)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 0, 0, 60))
                painter.drawPath(shadow_path)
            
            # Draw bubble background
            bubble_path = self._create_bubble_path(bubble)
            painter.setPen(QPen(self.bubble_color.darker(120), 2))
            painter.setBrush(self.bubble_color)
            painter.drawPath(bubble_path)
            
            # Draw spike/pointer
            if self.spike_enabled:
                spike_tip = self.spike_tip
                spike_base_x = bubble.center().x()
                spike_base_y = bubble.bottom()
                
                spike_path = QPainterPath()
                if self.hand_drawn:
                    spike_path.moveTo(self._wobble_point(QPointF(spike_base_x - self._spike_size / 2, spike_base_y), 100))
                    spike_path.lineTo(self._wobble_point(spike_tip, 101))
                    spike_path.lineTo(self._wobble_point(QPointF(spike_base_x + self._spike_size / 2, spike_base_y), 102))
                else:
                    spike_path.moveTo(spike_base_x - self._spike_size / 2, spike_base_y)
                    spike_path.lineTo(spike_tip)
                    spike_path.lineTo(spike_base_x + self._spike_size / 2, spike_base_y)
                spike_path.closeSubpath()
                
                painter.setPen(QPen(self.bubble_color.darker(120), 2))
                painter.setBrush(self.bubble_color)
                painter.drawPath(spike_path)
        
        # Draw text
        font = self._get_font()
        painter.setFont(font)
        
        text_color = self._get_contrasting_text_color()
        painter.setPen(text_color)
        
        # Draw multi-line text
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        lines = self._text.split('\n') if self._text else ['']
        y = self._position.y()
        for line in lines:
            painter.drawText(QPointF(self._position.x(), y), line)
            y += metrics.height()
        
        painter.restore()
    
    def randomize_hand_drawn(self) -> None:
        """Randomize the hand-drawn seed for a different wobble effect."""
        import random
        self.hand_drawn_seed = random.randint(0, 100000)
        self._cached_rect = None
    
    def toggle_hand_drawn(self) -> None:
        """Toggle hand-drawn style on/off."""
        self.hand_drawn = not self.hand_drawn
        self._cached_rect = None
    
    def hit_test(self, point: QPointF) -> bool:
        return self.bounding_rect.contains(point)
    
    def hit_test_spike_handle(self, point: QPointF) -> bool:
        """Test if point is on the spike handle."""
        if not self.spike_enabled:
            return False
        spike_tip = self.spike_tip
        handle_rect = QRectF(spike_tip.x() - 6, spike_tip.y() - 6, 12, 12)
        return handle_rect.contains(point)
    
    def move_spike(self, new_tip: QPointF) -> None:
        """Move the spike tip to a new position."""
        bubble = self.bubble_rect
        self.spike_offset = QPointF(
            new_tip.x() - bubble.center().x(),
            new_tip.y() - bubble.bottom()
        )
        self._cached_rect = None
    
    def move_by(self, dx: float, dy: float) -> None:
        self._position = QPointF(self._position.x() + dx, self._position.y() + dy)
        self._cached_rect = None
    
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        # For text, adjust font size based on handle drag
        # Could implement font size adjustment here
        pass
    
    def get_resize_handles(self) -> List[QRectF]:
        """Get handles including spike handle."""
        rect = self.bubble_rect
        handle_size = 8
        half = handle_size / 2
        
        handles = [
            QRectF(rect.left() - half, rect.top() - half, handle_size, handle_size),
            QRectF(rect.right() - half, rect.top() - half, handle_size, handle_size),
            QRectF(rect.left() - half, rect.bottom() - half, handle_size, handle_size),
            QRectF(rect.right() - half, rect.bottom() - half, handle_size, handle_size),
        ]
        
        return handles
    
    def get_spike_handle(self) -> QRectF:
        """Get the spike handle rectangle."""
        spike_tip = self.spike_tip
        return QRectF(spike_tip.x() - 5, spike_tip.y() - 5, 10, 10)
    
    def clone(self) -> "TextAnnotation":
        cloned = TextAnnotation(
            QPointF(self._position), self._text, self.style.clone()
        )
        cloned.z_index = self.z_index
        cloned.show_bubble = self.show_bubble
        cloned.bubble_color = QColor(self.bubble_color)
        cloned.bubble_radius = self.bubble_radius
        cloned.bubble_padding = self.bubble_padding
        cloned.spike_enabled = self.spike_enabled
        cloned.spike_offset = QPointF(self.spike_offset)
        cloned.hand_drawn = self.hand_drawn
        cloned.hand_drawn_seed = self.hand_drawn_seed
        cloned.show_shadow = self.show_shadow
        return cloned


# ─── Phase 3 Annotations ──────────────────────────────────────────────────────


class FreehandAnnotation(AnnotationBase):
    """
    Freehand drawing annotation - a smooth polyline path.
    
    Stores a list of points that form the path.
    """
    
    def __init__(
        self,
        points: Optional[List[QPointF]] = None,
        style: Optional[AnnotationStyle] = None
    ) -> None:
        super().__init__(style)
        self._points: List[QPointF] = points or []
        self._cached_path: Optional[QPainterPath] = None
        # TODO: hand_drawn_style flag for future jitter effect
        self.hand_drawn_style: bool = False
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.FREEHAND
    
    @property
    def points(self) -> List[QPointF]:
        return self._points
    
    def add_point(self, point: QPointF) -> None:
        """Add a point to the path."""
        self._points.append(point)
        self._cached_path = None
    
    @property
    def bounding_rect(self) -> QRectF:
        if not self._points:
            return QRectF()
        
        xs = [p.x() for p in self._points]
        ys = [p.y() for p in self._points]
        padding = self.style.stroke_width
        
        return QRectF(
            min(xs) - padding, min(ys) - padding,
            max(xs) - min(xs) + padding * 2,
            max(ys) - min(ys) + padding * 2
        )
    
    def _build_path(self) -> QPainterPath:
        """Build a smooth QPainterPath from points."""
        path = QPainterPath()
        if not self._points:
            return path
        
        path.moveTo(self._points[0])
        
        # Simple line-to for now; could use quadTo for smoother curves
        for point in self._points[1:]:
            path.lineTo(point)
        
        return path
    
    def paint(self, painter: QPainter) -> None:
        if not self._points:
            return
        
        if self._cached_path is None:
            self._cached_path = self._build_path()
        
        self._apply_style_to_pen(painter)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._cached_path)
    
    def hit_test(self, point: QPointF) -> bool:
        tolerance = max(self.style.stroke_width, 8)
        
        # Check distance to any line segment
        for i in range(len(self._points) - 1):
            if self._point_to_segment_distance(
                point, self._points[i], self._points[i + 1]
            ) <= tolerance:
                return True
        return False
    
    def _point_to_segment_distance(
        self, point: QPointF, seg_start: QPointF, seg_end: QPointF
    ) -> float:
        """Calculate distance from point to line segment."""
        dx = seg_end.x() - seg_start.x()
        dy = seg_end.y() - seg_start.y()
        length_sq = dx * dx + dy * dy
        
        if length_sq < 1:
            return math.sqrt(
                (point.x() - seg_start.x()) ** 2 +
                (point.y() - seg_start.y()) ** 2
            )
        
        t = max(0, min(1, (
            (point.x() - seg_start.x()) * dx +
            (point.y() - seg_start.y()) * dy
        ) / length_sq))
        
        closest_x = seg_start.x() + t * dx
        closest_y = seg_start.y() + t * dy
        
        return math.sqrt(
            (point.x() - closest_x) ** 2 +
            (point.y() - closest_y) ** 2
        )
    
    def move_by(self, dx: float, dy: float) -> None:
        self._points = [QPointF(p.x() + dx, p.y() + dy) for p in self._points]
        self._cached_path = None
    
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        # Freehand paths don't resize traditionally
        pass
    
    def get_resize_handles(self) -> List[QRectF]:
        # Just show corner handles of bounding rect
        rect = self.bounding_rect
        if rect.isEmpty():
            return []
        
        handle_size = 8
        half = handle_size / 2
        return [
            QRectF(rect.left() - half, rect.top() - half, handle_size, handle_size),
            QRectF(rect.right() - half, rect.top() - half, handle_size, handle_size),
            QRectF(rect.left() - half, rect.bottom() - half, handle_size, handle_size),
            QRectF(rect.right() - half, rect.bottom() - half, handle_size, handle_size),
        ]
    
    def clone(self) -> "FreehandAnnotation":
        cloned = FreehandAnnotation(
            [QPointF(p) for p in self._points],
            self.style.clone()
        )
        cloned.z_index = self.z_index
        cloned.hand_drawn_style = self.hand_drawn_style
        return cloned


class HighlightAnnotation(FreehandAnnotation):
    """
    Highlighter annotation with Multiply blend mode.
    
    Uses QPainter's CompositionMode_Multiply to ensure underlying text 
    remains crisp and black while only tinting the background.
    
    Features:
    - Multiply blend mode (not alpha transparency)
    - Thick stroke with rounded caps (marker effect)
    - Axis-locking for straight horizontal/vertical lines
    """
    
    def __init__(
        self,
        points: Optional[List[QPointF]] = None,
        style: Optional[AnnotationStyle] = None
    ) -> None:
        # Default highlighter style: yellow, wide
        if style is None:
            style = AnnotationStyle()
            style.stroke_color = QColor(255, 255, 0)  # Yellow
            style.stroke_width = 20
            style.opacity = 1.0  # Full opacity - blend mode handles tinting
        super().__init__(points, style)
        self.axis_locked: bool = False  # True if line was axis-locked
        self._lock_axis: Optional[str] = None  # 'h' for horizontal, 'v' for vertical
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.HIGHLIGHT
    
    def add_point_with_axis_lock(self, point: QPointF, threshold: float = 15.0) -> None:
        """
        Add a point with axis-locking algorithm.
        
        Detects near-horizontal or near-vertical mouse movement and snaps
        to a perfectly straight line to compensate for user input jitter.
        
        Args:
            point: The new point to add
            threshold: Angle threshold in degrees for axis detection
        """
        if len(self._points) == 0:
            self._points.append(point)
            self._cached_path = None
            return
        
        # Get the start point
        start = self._points[0]
        dx = point.x() - start.x()
        dy = point.y() - start.y()
        
        # Determine axis lock on first significant movement
        if self._lock_axis is None and len(self._points) < 3:
            distance = math.sqrt(dx * dx + dy * dy)
            if distance > 20:  # Minimum distance before locking
                angle = abs(math.degrees(math.atan2(abs(dy), abs(dx))))
                if angle < threshold:
                    self._lock_axis = 'h'  # Horizontal
                    self.axis_locked = True
                elif angle > (90 - threshold):
                    self._lock_axis = 'v'  # Vertical
                    self.axis_locked = True
        
        # Apply axis lock
        if self._lock_axis == 'h':
            # Lock to horizontal - keep y from start point
            point = QPointF(point.x(), start.y())
        elif self._lock_axis == 'v':
            # Lock to vertical - keep x from start point
            point = QPointF(start.x(), point.y())
        
        # Only keep start and current point for straight line when locked
        if self.axis_locked:
            if len(self._points) == 1:
                self._points.append(point)
            else:
                self._points[1] = point
        else:
            self._points.append(point)
        
        self._cached_path = None
    
    def paint(self, painter: QPainter) -> None:
        if not self._points:
            return
        
        if self._cached_path is None:
            self._cached_path = self._build_path()
        
        # Save painter state
        painter.save()
        
        # Use Multiply blend mode - keeps text crisp, only tints background
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        
        # Thick stroke with rounded caps for marker effect
        pen = QPen(self.style.stroke_color)
        pen.setWidth(self.style.stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        
        painter.setPen(pen)
        painter.setOpacity(self.style.opacity)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self._cached_path)
        
        # Restore painter state
        painter.restore()
    
    def clone(self) -> "HighlightAnnotation":
        cloned = HighlightAnnotation(
            [QPointF(p) for p in self._points],
            self.style.clone()
        )
        cloned.z_index = self.z_index
        cloned.axis_locked = self.axis_locked
        cloned._lock_axis = self._lock_axis
        return cloned


class SpotlightAnnotation(AnnotationBase):
    """
    Spotlight annotation - darkens outside the region, leaves inside bright.
    
    Creates a "spotlight" effect to draw attention to a specific area.
    """
    
    def __init__(
        self,
        rect: QRectF,
        style: Optional[AnnotationStyle] = None,
        is_circle: bool = False
    ) -> None:
        super().__init__(style)
        self._rect = rect.normalized()
        self.is_circle: bool = is_circle
        self.darkness: float = 0.6  # 0.0 to 1.0 - how dark outside area is
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.SPOTLIGHT
    
    @property
    def bounding_rect(self) -> QRectF:
        return self._rect
    
    @bounding_rect.setter
    def bounding_rect(self, rect: QRectF) -> None:
        self._rect = rect.normalized()
    
    def paint(self, painter: QPainter) -> None:
        # Spotlight paints a dark overlay with a hole
        # The actual painting is done by EditorCanvas which knows the image bounds
        # Here we just draw a dashed border to show the spotlight region
        pen = QPen(QColor(255, 255, 255, 180))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        if self.is_circle:
            painter.drawEllipse(self._rect)
        else:
            painter.drawRect(self._rect)
    
    def paint_overlay(self, painter: QPainter, image_bounds: QRectF) -> None:
        """
        Paint the spotlight overlay (called by canvas).
        
        Fills outside the spotlight region with dark overlay.
        """
        overlay_color = QColor(0, 0, 0, int(255 * self.darkness))
        
        # Create a path that covers everything except the spotlight
        path = QPainterPath()
        path.addRect(image_bounds)
        
        hole = QPainterPath()
        if self.is_circle:
            hole.addEllipse(self._rect)
        else:
            hole.addRect(self._rect)
        
        # Subtract the spotlight region
        path = path.subtracted(hole)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(overlay_color)
        painter.drawPath(path)
    
    def hit_test(self, point: QPointF) -> bool:
        # Hit test on the border
        tolerance = 10
        outer = self._rect.adjusted(-tolerance, -tolerance, tolerance, tolerance)
        inner = self._rect.adjusted(tolerance, tolerance, -tolerance, -tolerance)
        return outer.contains(point) and not inner.contains(point)
    
    def move_by(self, dx: float, dy: float) -> None:
        self._rect.translate(dx, dy)
    
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        rect = self._rect
        if handle_index == 0:
            rect.setTopLeft(new_pos)
        elif handle_index == 1:
            rect.setTop(new_pos.y())
        elif handle_index == 2:
            rect.setTopRight(new_pos)
        elif handle_index == 3:
            rect.setLeft(new_pos.x())
        elif handle_index == 4:
            rect.setRight(new_pos.x())
        elif handle_index == 5:
            rect.setBottomLeft(new_pos)
        elif handle_index == 6:
            rect.setBottom(new_pos.y())
        elif handle_index == 7:
            rect.setBottomRight(new_pos)
        self._rect = rect.normalized()
    
    def clone(self) -> "SpotlightAnnotation":
        cloned = SpotlightAnnotation(QRectF(self._rect), self.style.clone(), self.is_circle)
        cloned.z_index = self.z_index
        cloned.darkness = self.darkness
        return cloned


class BlurRegionAnnotation(AnnotationBase):
    """
    Blur/Pixelate region annotation.
    
    Supports two modes:
    - 'blur': Gaussian blur (frosted glass effect)
    - 'pixelate': Pixelation effect (blocky)
    
    The blur mode creates a smooth, frosted glass appearance like in Shottr.
    """
    
    def __init__(
        self,
        rect: QRectF,
        style: Optional[AnnotationStyle] = None,
        mode: str = "blur"  # Default to blur for frosted effect
    ) -> None:
        super().__init__(style)
        self._rect = rect.normalized()
        self.mode: str = mode  # "blur" or "pixelate"
        self.intensity: int = 25  # Blur kernel size (must be odd) or pixel block size
        self._cached_result: Optional[QImage] = None
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.BLUR_REGION
    
    @property
    def bounding_rect(self) -> QRectF:
        return self._rect
    
    @bounding_rect.setter
    def bounding_rect(self, rect: QRectF) -> None:
        self._rect = rect.normalized()
        self._cached_result = None
    
    def create_pixelated_region(self, source_image: QImage) -> QImage:
        """
        Create a blurred or pixelated version of the region from source image.
        
        For blur mode, uses OpenCV GaussianBlur for a frosted glass effect.
        For pixelate mode, uses shrink-scale technique.
        """
        rect = self._rect.toRect()
        
        # Clamp to image bounds
        rect = rect.intersected(source_image.rect())
        if rect.isEmpty():
            return QImage()
        
        if self.mode == "blur":
            return self._create_gaussian_blur(source_image, rect)
        else:
            return self._create_pixelated(source_image, rect)
    
    def _create_gaussian_blur(self, source_image: QImage, rect) -> QImage:
        """
        Create Gaussian blur (frosted glass) effect using OpenCV.
        
        Uses multiple blur passes with high kernel size to achieve
        a strong frosted glass look similar to Shottr.
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            # Fallback to pixelate if OpenCV not available
            return self._create_pixelated(source_image, rect)
        
        # Extract region
        region = source_image.copy(rect)
        
        # Convert QImage to numpy array
        width = region.width()
        height = region.height()
        
        if width == 0 or height == 0:
            return QImage()
        
        if region.format() != QImage.Format.Format_RGBA8888:
            region = region.convertToFormat(QImage.Format.Format_RGBA8888)
        
        ptr = region.bits()
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4)).copy()
        
        # Convert RGBA to BGR for OpenCV
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        
        # Calculate kernel size (must be odd)
        # Higher intensity = stronger blur
        kernel_size = max(15, self.intensity * 2 + 1)
        if kernel_size % 2 == 0:
            kernel_size += 1
        # Cap kernel size to avoid excessive processing
        kernel_size = min(kernel_size, 99)
        
        # Apply multiple Gaussian blur passes for strong frosted effect
        blurred = bgr.copy()
        
        # First pass - heavy blur
        blurred = cv2.GaussianBlur(blurred, (kernel_size, kernel_size), 0)
        
        # Second pass - additional blur for frosted look
        blurred = cv2.GaussianBlur(blurred, (kernel_size, kernel_size), 0)
        
        # Third pass for very strong frosted effect
        if self.intensity >= 20:
            smaller_kernel = max(11, kernel_size // 2)
            if smaller_kernel % 2 == 0:
                smaller_kernel += 1
            blurred = cv2.GaussianBlur(blurred, (smaller_kernel, smaller_kernel), 0)
        
        # Convert back to RGBA
        rgba = cv2.cvtColor(blurred, cv2.COLOR_BGR2RGBA)
        
        # Create QImage from result
        result = QImage(
            rgba.data, width, height, width * 4,
            QImage.Format.Format_RGBA8888
        ).copy()
        
        return result
    
    def _create_pixelated(self, source_image: QImage, rect) -> QImage:
        """Create pixelation effect."""
        # Extract region
        region = source_image.copy(rect)
        
        # Pixelate: shrink then scale back up
        block_size = max(1, self.intensity)
        small_w = max(1, region.width() // block_size)
        small_h = max(1, region.height() // block_size)
        
        small = region.scaled(
            small_w, small_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        pixelated = small.scaled(
            region.width(), region.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        return pixelated
    
    def paint(self, painter: QPainter) -> None:
        # Draw subtle border to show the blur region when selected
        if self.selected:
            pen = QPen(QColor(128, 128, 255, 150))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DotLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._rect)
    
    def hit_test(self, point: QPointF) -> bool:
        return self._rect.contains(point)
    
    def move_by(self, dx: float, dy: float) -> None:
        self._rect.translate(dx, dy)
        self._cached_result = None
    
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        rect = self._rect
        if handle_index == 0:
            rect.setTopLeft(new_pos)
        elif handle_index == 1:
            rect.setTop(new_pos.y())
        elif handle_index == 2:
            rect.setTopRight(new_pos)
        elif handle_index == 3:
            rect.setLeft(new_pos.x())
        elif handle_index == 4:
            rect.setRight(new_pos.x())
        elif handle_index == 5:
            rect.setBottomLeft(new_pos)
        elif handle_index == 6:
            rect.setBottom(new_pos.y())
        elif handle_index == 7:
            rect.setBottomRight(new_pos)
        self._rect = rect.normalized()
        self._cached_result = None
    
    def clone(self) -> "BlurRegionAnnotation":
        cloned = BlurRegionAnnotation(QRectF(self._rect), self.style.clone(), self.mode)
        cloned.z_index = self.z_index
        cloned.intensity = self.intensity
        return cloned


class StepAnnotation(AnnotationBase):
    """
    Step/numbered badge annotation.
    
    Displays a numbered circle for step-by-step instructions.
    """
    
    def __init__(
        self,
        position: QPointF,
        number: int = 1,
        style: Optional[AnnotationStyle] = None
    ) -> None:
        super().__init__(style)
        self._position = position
        self.number: int = number
        self.radius: int = 16
        self.circle_color: QColor = QColor(255, 80, 80)
        self.text_color: QColor = QColor(255, 255, 255)
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.STEP
    
    @property
    def position(self) -> QPointF:
        return self._position
    
    @position.setter
    def position(self, pos: QPointF) -> None:
        self._position = pos
    
    @property
    def bounding_rect(self) -> QRectF:
        r = self.radius
        return QRectF(
            self._position.x() - r,
            self._position.y() - r,
            r * 2, r * 2
        )
    
    def paint(self, painter: QPainter) -> None:
        painter.setOpacity(self.style.opacity)
        
        # Draw filled circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.circle_color)
        painter.drawEllipse(self._position, self.radius, self.radius)
        
        # Draw number
        painter.setPen(self.text_color)
        font = QFont()
        font.setPixelSize(int(self.radius * 1.2))
        font.setBold(True)
        painter.setFont(font)
        
        text = str(self.number)
        rect = self.bounding_rect
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    
    def hit_test(self, point: QPointF) -> bool:
        dx = point.x() - self._position.x()
        dy = point.y() - self._position.y()
        return (dx * dx + dy * dy) <= (self.radius * self.radius)
    
    def move_by(self, dx: float, dy: float) -> None:
        self._position = QPointF(self._position.x() + dx, self._position.y() + dy)
    
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        # Steps don't resize, just move
        pass
    
    def get_resize_handles(self) -> List[QRectF]:
        # No resize handles for step annotations
        return []
    
    def clone(self) -> "StepAnnotation":
        cloned = StepAnnotation(QPointF(self._position), self.number, self.style.clone())
        cloned.z_index = self.z_index
        cloned.radius = self.radius
        cloned.circle_color = QColor(self.circle_color)
        cloned.text_color = QColor(self.text_color)
        return cloned


class RulerAnnotation(AnnotationBase):
    """
    Ruler/measurement annotation.
    
    Shows a line with distance measurement in pixels.
    """
    
    def __init__(
        self,
        start: QPointF,
        end: QPointF,
        style: Optional[AnnotationStyle] = None
    ) -> None:
        super().__init__(style)
        self._start = start
        self._end = end
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.RULER
    
    @property
    def start(self) -> QPointF:
        return self._start
    
    @start.setter
    def start(self, point: QPointF) -> None:
        self._start = point
    
    @property
    def end(self) -> QPointF:
        return self._end
    
    @end.setter
    def end(self, point: QPointF) -> None:
        self._end = point
    
    @property
    def distance(self) -> float:
        """Calculate the distance in pixels."""
        dx = self._end.x() - self._start.x()
        dy = self._end.y() - self._start.y()
        return math.sqrt(dx * dx + dy * dy)
    
    @property
    def bounding_rect(self) -> QRectF:
        padding = 20  # For text label
        left = min(self._start.x(), self._end.x()) - padding
        top = min(self._start.y(), self._end.y()) - padding
        right = max(self._start.x(), self._end.x()) + padding
        bottom = max(self._start.y(), self._end.y()) + padding
        return QRectF(left, top, right - left, bottom - top)
    
    def paint(self, painter: QPainter) -> None:
        self._apply_style_to_pen(painter)
        
        # Draw line
        painter.drawLine(self._start, self._end)
        
        # Draw endpoints (small circles)
        painter.setBrush(self.style.stroke_color)
        painter.drawEllipse(self._start, 4, 4)
        painter.drawEllipse(self._end, 4, 4)
        
        # Draw distance label at center
        center = QPointF(
            (self._start.x() + self._end.x()) / 2,
            (self._start.y() + self._end.y()) / 2
        )
        
        distance_text = f"{self.distance:.0f}px"
        
        # Background for text
        font = QFont()
        font.setPixelSize(12)
        painter.setFont(font)
        
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        text_rect = metrics.boundingRect(distance_text)
        
        bg_rect = QRectF(
            center.x() - text_rect.width() / 2 - 4,
            center.y() - text_rect.height() / 2 - 2,
            text_rect.width() + 8,
            text_rect.height() + 4
        )
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawRoundedRect(bg_rect, 3, 3)
        
        # Draw text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, distance_text)
    
    def hit_test(self, point: QPointF) -> bool:
        tolerance = 8
        
        dx = self._end.x() - self._start.x()
        dy = self._end.y() - self._start.y()
        length_sq = dx * dx + dy * dy
        
        if length_sq < 1:
            dist = math.sqrt(
                (point.x() - self._start.x()) ** 2 +
                (point.y() - self._start.y()) ** 2
            )
            return dist <= tolerance
        
        t = max(0, min(1, (
            (point.x() - self._start.x()) * dx +
            (point.y() - self._start.y()) * dy
        ) / length_sq))
        
        closest_x = self._start.x() + t * dx
        closest_y = self._start.y() + t * dy
        
        dist = math.sqrt(
            (point.x() - closest_x) ** 2 +
            (point.y() - closest_y) ** 2
        )
        return dist <= tolerance
    
    def move_by(self, dx: float, dy: float) -> None:
        self._start = QPointF(self._start.x() + dx, self._start.y() + dy)
        self._end = QPointF(self._end.x() + dx, self._end.y() + dy)
    
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        if handle_index in (0, 1, 3, 5):
            self._start = new_pos
        else:
            self._end = new_pos
    
    def get_resize_handles(self) -> List[QRectF]:
        handle_size = 8
        half = handle_size / 2
        return [
            QRectF(self._start.x() - half, self._start.y() - half, handle_size, handle_size),
            QRectF(self._end.x() - half, self._end.y() - half, handle_size, handle_size),
        ]
    
    def hit_test_handle(self, point: QPointF) -> int:
        handles = self.get_resize_handles()
        for i, handle in enumerate(handles):
            if handle.contains(point):
                return 0 if i == 0 else 7
        return -1
    
    def clone(self) -> "RulerAnnotation":
        cloned = RulerAnnotation(
            QPointF(self._start), QPointF(self._end), self.style.clone()
        )
        cloned.z_index = self.z_index
        return cloned


# ─── Backdrop Settings ─────────────────────────────────────────────────────────


@dataclass
class BackdropSettings:
    """
    Settings for the backdrop behind the screenshot.
    
    Creates a polished look with rounded corners, shadows, and gradient backgrounds.
    """
    enabled: bool = False
    corner_radius: int = 16
    shadow_blur: int = 20
    shadow_offset_x: int = 0
    shadow_offset_y: int = 10
    shadow_opacity: float = 0.5
    padding: int = 40  # Space around image for shadow/background
    background_color_1: QColor = field(default_factory=lambda: QColor(45, 45, 55))
    background_color_2: Optional[QColor] = None  # For gradient; None = solid color
    
    def clone(self) -> "BackdropSettings":
        return BackdropSettings(
            enabled=self.enabled,
            corner_radius=self.corner_radius,
            shadow_blur=self.shadow_blur,
            shadow_offset_x=self.shadow_offset_x,
            shadow_offset_y=self.shadow_offset_y,
            shadow_opacity=self.shadow_opacity,
            padding=self.padding,
            background_color_1=QColor(self.background_color_1),
            background_color_2=QColor(self.background_color_2) if self.background_color_2 else None,
        )


# ─── Content-Aware Inpaint Annotation ──────────────────────────────────────────


class InpaintAnnotation(AnnotationBase):
    """
    Content-aware inpainting annotation.
    
    Uses OpenCV's inpainting algorithms (Telea or Navier-Stokes) to
    reconstruct the masked region by analyzing boundary pixels.
    This creates a seamless "healing" effect.
    """
    
    ALGO_TELEA = "telea"  # Fast, good for small regions
    ALGO_NS = "ns"  # Navier-Stokes, smoother but slower
    
    def __init__(
        self,
        rect: QRectF,
        style: Optional[AnnotationStyle] = None,
        algorithm: str = "telea"
    ) -> None:
        super().__init__(style)
        self._rect = rect.normalized()
        self.algorithm: str = algorithm
        self.inpaint_radius: int = 5  # Radius of pixels to consider for inpainting
        self._cached_result: Optional[QImage] = None
    
    @property
    def annotation_type(self) -> AnnotationType:
        return AnnotationType.INPAINT
    
    @property
    def bounding_rect(self) -> QRectF:
        return self._rect
    
    @bounding_rect.setter
    def bounding_rect(self, rect: QRectF) -> None:
        self._rect = rect.normalized()
        self._cached_result = None
    
    def perform_inpaint(self, source_image: QImage) -> QImage:
        """
        Perform content-aware inpainting on the masked region.
        
        Uses OpenCV's inpainting algorithms to reconstruct the region
        by analyzing boundary pixels.
        
        Args:
            source_image: The source QImage to inpaint.
            
        Returns:
            A new QImage with the region inpainted.
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            # Fallback: return original if OpenCV not available
            return source_image
        
        # Convert QImage to numpy array
        result_image = source_image.copy()
        
        # Get region bounds
        rect = self._rect.toRect()
        rect = rect.intersected(source_image.rect())
        if rect.isEmpty():
            return source_image
        
        # Convert full image to numpy (OpenCV format)
        width = source_image.width()
        height = source_image.height()
        
        # Convert QImage to numpy array
        ptr = source_image.bits()
        if source_image.format() != QImage.Format.Format_RGBA8888:
            temp = source_image.convertToFormat(QImage.Format.Format_RGBA8888)
            ptr = temp.bits()
            arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4)).copy()
        else:
            arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4)).copy()
        
        # Convert RGBA to BGR for OpenCV
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        
        # Create mask (white = area to inpaint)
        mask = np.zeros((height, width), dtype=np.uint8)
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        mask[y:y+h, x:x+w] = 255
        
        # Choose algorithm
        if self.algorithm == self.ALGO_NS:
            flag = cv2.INPAINT_NS
        else:
            flag = cv2.INPAINT_TELEA
        
        # Perform inpainting
        inpainted = cv2.inpaint(bgr, mask, self.inpaint_radius, flag)
        
        # Convert back to RGBA
        rgba = cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGBA)
        
        # Create QImage from result
        result = QImage(
            rgba.data, width, height, width * 4,
            QImage.Format.Format_RGBA8888
        ).copy()  # .copy() to own the data
        
        return result
    
    def paint(self, painter: QPainter) -> None:
        # Draw a dashed rectangle to show the inpaint region (temporary visual)
        pen = QPen(QColor(255, 100, 100, 150))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashDotLine)
        painter.setPen(pen)
        painter.setBrush(QColor(255, 100, 100, 30))
        painter.drawRect(self._rect)
    
    def hit_test(self, point: QPointF) -> bool:
        return self._rect.contains(point)
    
    def move_by(self, dx: float, dy: float) -> None:
        self._rect.translate(dx, dy)
        self._cached_result = None
    
    def resize(self, handle_index: int, new_pos: QPointF) -> None:
        rect = self._rect
        if handle_index == 0:
            rect.setTopLeft(new_pos)
        elif handle_index == 1:
            rect.setTop(new_pos.y())
        elif handle_index == 2:
            rect.setTopRight(new_pos)
        elif handle_index == 3:
            rect.setLeft(new_pos.x())
        elif handle_index == 4:
            rect.setRight(new_pos.x())
        elif handle_index == 5:
            rect.setBottomLeft(new_pos)
        elif handle_index == 6:
            rect.setBottom(new_pos.y())
        elif handle_index == 7:
            rect.setBottomRight(new_pos)
        self._rect = rect.normalized()
        self._cached_result = None
    
    def clone(self) -> "InpaintAnnotation":
        cloned = InpaintAnnotation(QRectF(self._rect), self.style.clone(), self.algorithm)
        cloned.z_index = self.z_index
        cloned.inpaint_radius = self.inpaint_radius
        return cloned
