
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QStandardItemModel
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
    
    def flags(self, index):
        """Return item flags for the given index."""
        if not index.isValid():
            return Qt.NoItemFlags
        
        default_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
        # Make title column editable
        if index.column() == self.COL_TITLE:
            default_flags |= Qt.ItemIsEditable
        
        # Enable drag and drop
        default_flags |= Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        
        return default_flags
    
    def supportedDropActions(self):
        """Return the supported drop actions."""
        return Qt.MoveAction | Qt.CopyAction
    
    def supportedDragActions(self):
        """Return the supported drag actions."""
        return Qt.MoveAction
    
    def mimeTypes(self):
        """Return the supported mime types."""
        return ["application/x-omneva-playitem"]
    
    def mimeData(self, indexes):
        """Return mime data for the given indexes."""
        mime_data = QStandardItemModel.mimeData(self, indexes)
        
        # Store row indices as plain text for internal moves
        rows = [str(index.row()) for index in indexes if index.isValid()]
        if rows:
            mime_data.setText(",".join(rows))
        
        return mime_data
    
    def dropMimeData(self, mime_data, action, row, parent):
        """Handle drop of mime data."""
        if action == Qt.IgnoreAction:
            return True
        
        if not mime_data.hasFormat("application/x-omneva-playitem"):
            return False
        
        # Handle internal move
        if mime_data.hasText():
            try:
                rows = [int(r.strip()) for r in mime_data.text().split(",") if r.strip().isdigit()]
                if not rows:
                    return False
                
                # Sort rows to maintain order
                rows.sort()
                
                # Determine target row
                if parent.isValid():
                    target_row = parent.row()
                else:
                    target_row = row if row >= 0 else self.rowCount()
                
                # Move items
                return self._move_rows(rows, target_row)
                
            except (ValueError, IndexError):
                return False
        
        return False
    
    def _move_rows(self, source_rows, target_row):
        """Move rows from source positions to target position."""
        if not source_rows:
            return False
        
        # Validate target row
        if target_row < 0:
            target_row = 0
        elif target_row > self.rowCount():
            target_row = self.rowCount()
        
        # Collect items to move
        items_to_move = []
        for row in source_rows:
            if 0 <= row < len(self._data):
                items_to_move.append(self._data[row])
        
        if not items_to_move:
            return False
        
        # Remove items from original positions (in reverse order to maintain indices)
        rows_to_remove = sorted(source_rows, reverse=True)
        for row in rows_to_remove:
            if 0 <= row < len(self._data):
                self.beginRemoveRows(QModelIndex(), row, row)
                self._data.pop(row)
                self.endRemoveRows()
                
                # Adjust current index
                if self._current_index == row:
                    self._current_index = -1
                elif self._current_index > row:
                    self._current_index -= 1
        
        # Insert items at target position
        # Adjust target row for removed items
        adjusted_target = target_row
        for row in source_rows:
            if row < target_row:
                adjusted_target -= 1
        
        # Insert items
        for i, item in enumerate(items_to_move):
            insert_row = adjusted_target + i
            self.beginInsertRows(QModelIndex(), insert_row, insert_row)
            self._data.insert(insert_row, item)
            self.endInsertRows()
            
            # Adjust current index
            if self._current_index >= insert_row:
                self._current_index += 1
        
        # Find new current index if needed
        if self._current_index == -1 and items_to_move:
            # Try to find one of the moved items
            for i, item in enumerate(items_to_move):
                for row, data_item in enumerate(self._data):
                    if data_item['path'] == item['path']:
                        self._current_index = row
                        break
                if self._current_index != -1:
                    break
        
        return True
    
    def setData(self, index, value, role=Qt.EditRole):
        """Set data for the given index and role."""
        if not index.isValid() or role != Qt.EditRole:
            return False
        
        if not (0 <= index.row() < len(self._data)):
            return False
        
        item = self._data[index.row()]
        col = index.column()
        
        if col == self.COL_TITLE:
            # Update the title
            old_title = item['title']
            item['title'] = str(value).strip()
            
            # Emit dataChanged signal
            self.dataChanged.emit(index, index)
            
            # Log the change for debugging
            print(f"Playlist item renamed: '{old_title}' -> '{item['title']}'")
            return True
        
        return False

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

    def update_metadata_batch(self, updates: list):
        """Update metadata for multiple items in a single batch operation.
        
        Args:
            updates: List of tuples (path, duration, album) where duration/album can be None
        """
        if not updates:
            return
            
        # Collect rows that need updating
        rows_to_update = []
        
        for path, duration, album in updates:
            for row, item in enumerate(self._data):
                if item['path'] == path:
                    updated = False
                    if duration is not None and item['duration'] != duration:
                        item['duration'] = duration
                        updated = True
                    if album is not None and item['album'] != album:
                        item['album'] = album
                        updated = True
                    
                    if updated:
                        rows_to_update.append(row)
                    break
        
        # Emit single dataChanged for all updated rows
        if rows_to_update:
            min_row = min(rows_to_update)
            max_row = max(rows_to_update)
            self.dataChanged.emit(
                self.index(min_row, 0),
                self.index(max_row, self.columnCount()-1)
            )

    def add_files_batch(self, files: list):
        """Add multiple files to the playlist in a single batch operation.
        
        Args:
            files: List of tuples (path, duration, album) where duration/album can be None
        """
        if not files:
            return
            
        start_row = len(self._data)
        new_items = []
        
        for path, duration, album in files:
            # Check for existing duplicates
            exists = False
            for item in self._data:
                if item['path'] == path:
                    exists = True
                    break
            
            if not exists:
                new_items.append({
                    'path': path,
                    'title': os.path.basename(path),
                    'duration': duration or 0,
                    'album': album or ""
                })
        
        if new_items:
            self.beginInsertRows(QModelIndex(), start_row, start_row + len(new_items) - 1)
            self._data.extend(new_items)
            self.endInsertRows()

    def clear_with_reset(self):
        """Clear the playlist using beginResetModel/endResetModel for large datasets."""
        self.beginResetModel()
        self._data.clear()
        self._current_index = -1
        self.endResetModel()
