"""
Custom seek slider with chapter markers support.
"""

from typing import List, Dict, Optional
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QFont, QPaintEvent, QPainter, QPen, QColor


class ChapterSlider(QSlider):
    """
    Custom QSlider that displays chapter markers as tick marks on the timeline.
    """
    
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.chapters: List[Dict] = []
        self._hovered_chapter: Optional[Dict] = None
        self.setMouseTracking(True)
        
        # Style configuration
        self._tick_color = QColor(100, 100, 100)
        self._tick_height = 8
        self._tick_width = 2
        self._hover_color = QColor(70, 130, 180)
        self._font = QFont("Arial", 8)
        
    def set_chapters(self, chapters: List[Dict]):
        """
        Set chapter data and trigger repaint.
        
        Args:
            chapters: List of chapter dicts with 'start', 'end', 'title' keys
        """
        self.chapters = chapters
        self.update()
        
    def clear_chapters(self):
        """Clear all chapter markers."""
        self.chapters = []
        self._hovered_chapter = None
        self.update()
        
    def get_chapter_at_position(self, position: int) -> Optional[Dict]:
        """
        Get chapter at the given slider position.
        
        Args:
            position: Slider position (0 to maximum())
            
        Returns:
            Chapter dict or None if no chapter at position
        """
        if not self.chapters or self.maximum() == 0:
            return None
            
        # Convert position to time in seconds
        time_seconds = position / 1000.0
        
        # Find chapter at this time
        for chapter in self.chapters:
            if chapter['start'] <= time_seconds <= chapter['end']:
                return chapter
                
        return None
        
    def mouseMoveEvent(self, event):
        """Handle mouse move to show chapter tooltips."""
        if self.chapters:
            chapter = self.get_chapter_at_position(event.position().x())
            if chapter != self._hovered_chapter:
                self._hovered_chapter = chapter
                self.update()
                
                # Update tooltip
                if chapter and chapter.get('title'):
                    start_time = int(chapter['start'])
                    self.setToolTip(f"{chapter['title']}\n{start_time // 60:02d}:{start_time % 60:02d}")
                else:
                    self.setToolTip("")
        else:
            self._hovered_chapter = None
            self.setToolTip("")
            
        super().mouseMoveEvent(event)
        
    def paintEvent(self, event: QPaintEvent):
        """Override paint to draw chapter markers."""
        super().paintEvent(event)
        
        if not self.chapters:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get slider geometry
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        
        # Calculate groove rect (the track area)
        groove_rect = self.style().subControlRect(
            QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self
        )
        
        if not groove_rect.isValid():
            return
            
        # Draw chapter markers
        max_value = self.maximum()
        if max_value == 0:
            return
            
        for i, chapter in enumerate(self.chapters):
            # Calculate position as percentage of slider width
            start_pos = int((chapter['start'] * 1000) / max_value * groove_rect.width())
            
            # Clamp to groove bounds
            x = groove_rect.left() + start_pos
            x = max(groove_rect.left(), min(x, groove_rect.right()))
            
            # Determine color and height based on hover state
            if self._hovered_chapter == chapter:
                color = self._hover_color
                height = self._tick_height + 2
            else:
                color = self._tick_color
                height = self._tick_height
                
            # Draw tick mark
            painter.setPen(QPen(color, self._tick_width))
            painter.drawLine(
                x, groove_rect.center().y() - height // 2,
                x, groove_rect.center().y() + height // 2
            )
            
            # Draw chapter title for hovered chapter
            if self._hovered_chapter == chapter and chapter.get('title'):
                painter.setFont(self._font)
                painter.setPen(QPen(color))
                
                # Calculate text position
                text_rect = painter.boundingRect(
                    QRect(), Qt.AlignCenter, chapter['title']
                )
                
                # Position text above the tick
                text_y = groove_rect.top() - text_rect.height() - 5
                text_x = x - text_rect.width() // 2
                
                # Ensure text stays within widget bounds
                text_x = max(0, min(text_x, self.width() - text_rect.width()))
                text_y = max(0, text_y)
                
                # Draw background for better readability
                bg_rect = text_rect.adjusted(-2, -1, 2, 1)
                bg_rect.moveTo(text_x - 2, text_y - 1)
                painter.fillRect(bg_rect, QColor(255, 255, 255, 200))
                
                # Draw text
                painter.drawText(text_x, text_y + text_rect.height(), chapter['title'])
                
    def leaveEvent(self, event):
        """Handle mouse leave to clear hover state."""
        self._hovered_chapter = None
        self.setToolTip("")
        self.update()
        super().leaveEvent(event)
