"""
Chapters Tab — HandBrake-style chapter markers management.
Displays chapter list from source file with editable names.
Supports import/export of chapter markers (CSV format).
"""
import csv
import io
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QFileDialog, QFrame,
)
from PySide6.QtCore import Qt


class ChaptersTab(QWidget):
    """Chapters tab with chapter list table and import/export."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chapters: list[dict] = []
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ─── Toolbar ─────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.chk_chapters = QCheckBox("Include Chapter Markers")
        self.chk_chapters.setChecked(True)
        self.chk_chapters.setStyleSheet("color: #ddd; font-size: 12px;")
        self.chk_chapters.toggled.connect(self._on_toggle)
        toolbar.addWidget(self.chk_chapters)

        toolbar.addStretch()

        self.btn_import = QPushButton("Import …")
        self.btn_import.setFixedHeight(28)
        self.btn_import.setToolTip("Import chapter markers from CSV file")
        self.btn_import.clicked.connect(self._import_chapters)
        toolbar.addWidget(self.btn_import)

        self.btn_export = QPushButton("Export …")
        self.btn_export.setFixedHeight(28)
        self.btn_export.setToolTip("Export chapter markers to CSV file")
        self.btn_export.clicked.connect(self._export_chapters)
        toolbar.addWidget(self.btn_export)

        self.btn_reset = QPushButton("Reset Names")
        self.btn_reset.setFixedHeight(28)
        self.btn_reset.setToolTip("Reset all chapter names to default")
        self.btn_reset.clicked.connect(self._reset_names)
        toolbar.addWidget(self.btn_reset)

        main_layout.addLayout(toolbar)

        # ─── Separator ───────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #444;")
        main_layout.addWidget(sep)

        # ─── Chapter Table ───────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["#", "Start Time", "Chapter Name"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 120)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #1e1e1e; border: 1px solid #333;
                gridline-color: #333; color: #ddd;
            }
            QTableWidget::item { padding: 4px; }
            QTableWidget::item:selected { background: #2a5a8a; }
            QHeaderView::section {
                background: #2a2a2a; color: #aaa;
                border: 1px solid #333; padding: 4px;
                font-weight: bold; font-size: 11px;
            }
        """)
        main_layout.addWidget(self.table, 1)

        # ─── Info label ──────────────────────────────────────
        self.lbl_info = QLabel("No chapters detected. Load a source file to see chapters.")
        self.lbl_info.setStyleSheet("color: #666; font-size: 11px;")
        main_layout.addWidget(self.lbl_info)

    # ── Toggle ───────────────────────────────────────────────

    def _on_toggle(self, checked: bool):
        """Enable/disable the chapter table when checkbox is toggled."""
        self.table.setEnabled(checked)
        self.btn_import.setEnabled(checked)
        self.btn_export.setEnabled(checked)
        self.btn_reset.setEnabled(checked)

    # ── Load from FFprobe ────────────────────────────────────

    def load_chapters(self, chapters: list[dict]):
        """Load chapters from FFprobe metadata.
        Each dict should have: id, start_time, end_time, tags.title"""
        self._chapters = chapters
        self.table.setRowCount(len(chapters))

        for row, ch in enumerate(chapters):
            start = float(ch.get("start_time", 0))
            title = ch.get("tags", {}).get("title", f"Chapter {row + 1}")

            # Chapter number (read-only)
            num_item = QTableWidgetItem(str(row + 1))
            num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
            num_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, num_item)

            # Start time (read-only, formatted)
            time_str = self._format_time(start)
            time_item = QTableWidgetItem(time_str)
            time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
            time_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, time_item)

            # Chapter name (editable)
            name_item = QTableWidgetItem(title)
            self.table.setItem(row, 2, name_item)

        count = len(chapters)
        if count > 0:
            self.lbl_info.setText(f"{count} chapter{'s' if count != 1 else ''} detected.")
        else:
            self.lbl_info.setText("No chapters detected in source file.")

    # ── Import / Export ──────────────────────────────────────

    def _import_chapters(self):
        """Import chapter names from a CSV file (Chapter Number, Name)."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Chapters", "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)",
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for csv_row in reader:
                    if len(csv_row) >= 2:
                        try:
                            idx = int(csv_row[0]) - 1
                            name = csv_row[1].strip()
                            if 0 <= idx < self.table.rowCount():
                                self.table.item(idx, 2).setText(name)
                        except (ValueError, AttributeError):
                            pass
        except Exception:
            pass

    def _export_chapters(self):
        """Export chapter markers to CSV."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Chapters", "chapters.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Chapter", "Start Time", "Name"])
                for row in range(self.table.rowCount()):
                    num = self.table.item(row, 0).text()
                    time = self.table.item(row, 1).text()
                    name = self.table.item(row, 2).text()
                    writer.writerow([num, time, name])
        except Exception:
            pass

    def _reset_names(self):
        """Reset all chapter names to default 'Chapter N'."""
        for row in range(self.table.rowCount()):
            self.table.item(row, 2).setText(f"Chapter {row + 1}")

    # ── Settings ─────────────────────────────────────────────

    def get_settings(self) -> dict:
        """Return chapter settings."""
        chapters = []
        for row in range(self.table.rowCount()):
            chapters.append({
                "number":     int(self.table.item(row, 0).text()),
                "start_time": self.table.item(row, 1).text(),
                "name":       self.table.item(row, 2).text(),
            })
        return {
            "include_chapters": self.chk_chapters.isChecked(),
            "chapters": chapters,
        }

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds to HH:MM:SS.mmm."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}"
