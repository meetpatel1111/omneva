
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from src.core.utils import format_duration
import os

class PlaylistModel(QAbstractTableModel):
    """Table model for the playlist (Title, Duration, Album)."""

    COL_TITLE = 0
    COL_DURATION = 1
    COL_ALBUM = 2
    
    COLUMNS = ["Title", "Duration", "Album"]

    # Signals
    current_changed = Signal(int) # Emits row index of current playing item

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = [] # List of dicts: {'path': str, 'title': str, 'duration': float, 'album': str}
        self._current_index = -1

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        item = self._data[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == self.COL_TITLE:
                return item['title']
            elif col == self.COL_DURATION:
                if item['duration'] > 0:
                    return format_duration(item['duration'])
                return "--:--"
            elif col == self.COL_ALBUM:
                return item['album']
        
        elif role == Qt.ToolTipRole:
            return item['path']
        
        elif role == Qt.UserRole:
            return item['path']

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None

    def add_file(self, path: str, duration: float = 0, album: str = ""):
        """Add a file to the playlist."""
        # Avoid duplicates if desired, or allow them. VLC allows duplicates.
        # Let's check if path exists to avoid adding same file twice?
        # User might want to play same song twice. Let's allow duplicates for now, 
        # or stick to unique paths for simplicity.
        # The user's code earlier used `if path not in self._files`.
        
        # Check for existing
        for row, item in enumerate(self._data):
            if item['path'] == path:
                return row # Return existing index

        row = len(self._data)
        self.beginInsertRows(QModelIndex(), row, row)
        self._data.append({
            'path': path,
            'title': os.path.basename(path),
            'duration': duration,
            'album': album
        })
        self.endInsertRows()
        return row

    def get_path(self, row: int):
        if 0 <= row < len(self._data):
            return self._data[row]['path']
        return None

    def set_current_index(self, index: int):
        self._current_index = index
        self.current_changed.emit(index)

    def get_current_index(self):
        return self._current_index

    def remove_at(self, row: int):
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._data.pop(row)
            self.endRemoveRows()
            
            # Adjust current index
            if self._current_index == row:
                self._current_index = -1
            elif self._current_index > row:
                self._current_index -= 1

    def clear(self):
        self.beginResetModel()
        self._data.clear()
        self._current_index = -1
        self.endResetModel()

    def update_metadata(self, path, duration=None, album=None):
        """Update metadata for an item (e.g. after loading)."""
        for row, item in enumerate(self._data):
            if item['path'] == path:
                if duration is not None:
                    item['duration'] = duration
                if album is not None:
                    item['album'] = album
                # Notify change
                self.dataChanged.emit(
                    self.index(row, 0),
                    self.index(row, self.columnCount()-1)
                )
                break
