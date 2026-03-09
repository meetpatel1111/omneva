"""History Service — Manages playback history and recent media."""

import os
from PySide6.QtCore import QObject, Signal
from src.core.storage import storage

class HistoryService(QObject):
    """Manages playback history stacks and recent media persistence."""
    
    history_updated = Signal()

    def __init__(self, max_recent: int = 10):
        super().__init__()
        self.max_recent = max_recent
        self._history_stack = []
        self._forward_stack = []
        self._current_media = None

    def add_media(self, file_path: str, push_history: bool = True):
        """Register a new media file being played."""
        if not file_path or not os.path.exists(file_path):
            return

        if push_history and self._current_media:
            self._history_stack.append(self._current_media)
            self._forward_stack.clear()
        
        self._current_media = file_path
        storage.add_to_history(file_path)
        self.history_updated.emit()

    def go_back(self) -> str | None:
        """Move back in history and return the file path."""
        if not self._history_stack:
            return None
        
        if self._current_media:
            self._forward_stack.append(self._current_media)
        
        self._current_media = self._history_stack.pop()
        return self._current_media

    def go_forward(self) -> str | None:
        """Move forward in history and return the file path."""
        if not self._forward_stack:
            return None
        
        if self._current_media:
            self._history_stack.append(self._current_media)
        
        self._current_media = self._forward_stack.pop()
        return self._current_media

    def get_recent(self) -> list[str]:
        """Get the list of recent files from storage."""
        return storage.get_history(limit=self.max_recent)

    def clear_recent(self):
        """Clear all recent media history."""
        storage.clear_history()
        self._history_stack.clear()
        self._forward_stack.clear()
        self._current_media = None
        self.history_updated.emit()

    @property
    def current_media(self):
        return self._current_media
