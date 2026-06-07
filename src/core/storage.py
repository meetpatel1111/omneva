"""Storage manager — handles QSettings (INI) and SQLite database in AppData."""

import os
import sqlite3
from PySide6.QtCore import QSettings, QStandardPaths
from .logger import get_logger

class StorageManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StorageManager, cls).__new__(cls)
            cls._instance.app_data_dir = None
            cls._instance.settings_path = None
            cls._instance.db_path = None
            cls._instance.logger = get_logger('storage')
        return cls._instance

    def _ensure_initialized(self):
        """Initialize paths and database if not already done."""
        if self.app_data_dir:
            return

        # Get AppData location (e.g., %APPDATA%/Omneva or ~/.local/share/Omneva)
        # Accessing this AFTER QApplication setup ensures it respects Organization/App Name
        self.app_data_dir = QStandardPaths.writableLocation(
            QStandardPaths.AppDataLocation
        )
        if not self.app_data_dir:
            # Fallback if Qt fails
            self.app_data_dir = os.path.join(os.path.expanduser("~"), ".omneva")
        
        # Ensure directories exist
        if not os.path.exists(self.app_data_dir):
            try:
                os.makedirs(self.app_data_dir)
            except OSError as e:
                self.logger.error(f"Failed to create AppData dir: {e}")

        # Paths
        self.settings_path = os.path.join(self.app_data_dir, "config.ini")
        self.db_path = os.path.join(self.app_data_dir, "omneva.db")

        self.logger.info(f"AppData: {self.app_data_dir}")
        self.logger.info(f"Settings: {self.settings_path}")
        self.logger.info(f"Database: {self.db_path}")

        # Initialize SQLite
        self._init_db()

    def get_settings(self) -> QSettings:
        """Return QSettings instance using the local INI file."""
        self._ensure_initialized()
        return QSettings(self.settings_path, QSettings.IniFormat)

    def _init_db(self):
        """Create tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # History table
            c.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    position REAL DEFAULT 0.0
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"DB Init Error: {e}")

    # ─── History API ─────────────────────────────────────────

    def add_to_history(self, path: str):
        """Add or update a file in history."""
        self._ensure_initialized()
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Upsert logic (delete then insert to update timestamp)
            c.execute("DELETE FROM history WHERE path = ?", (path,))
            c.execute("INSERT INTO history (path) VALUES (?)", (path,))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Add History Error: {e}")

    def get_history(self, limit=10) -> list[str]:
        """Get list of recent file paths."""
        self._ensure_initialized()
        paths = []
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT path FROM history ORDER BY last_played DESC LIMIT ?", (limit,))
            rows = c.fetchall()
            paths = [row[0] for row in rows]
            conn.close()
        except Exception as e:
            self.logger.error(f"Get History Error: {e}")
        return paths

    def clear_history(self):
        """Clear all history."""
        self._ensure_initialized()
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("DELETE FROM history")
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Clear History Error: {e}")

# Global instance header
storage = StorageManager()
