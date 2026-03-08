"""Queue Panel — Dedicated job queue view for all transcoding/conversion jobs."""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QScrollArea
)
from PySide6.QtCore import Qt, Signal


class JobItem(QFrame):
    """Widget for a single job in the queue list."""

    def __init__(self, job_id: str, filename: str, preset_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("jobItem")
        self.job_id = job_id
        self.setFixedHeight(60)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        # Top row: filename + preset + status
        top = QHBoxLayout()
        self.lbl_name = QLabel(f"📄 {filename}")
        self.lbl_name.setObjectName("jobName")
        self.lbl_preset = QLabel(preset_name)
        self.lbl_preset.setObjectName("jobSpeed")
        self.lbl_preset.setFixedWidth(140)
        self.lbl_status = QLabel("Pending")
        self.lbl_status.setObjectName("jobStatus")
        top.addWidget(self.lbl_name, 1)
        top.addWidget(self.lbl_preset)
        top.addWidget(self.lbl_status)
        layout.addLayout(top)

        # Bottom row: progress + speed
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.progress = QProgressBar()
        self.progress.setObjectName("jobProgress")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(14)

        self.lbl_speed = QLabel("")
        self.lbl_speed.setObjectName("jobSpeed")
        self.lbl_speed.setFixedWidth(70)
        self.lbl_speed.setAlignment(Qt.AlignRight)

        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.lbl_speed)
        layout.addLayout(bottom)

    def update_progress(self, percent: float, speed: str = ""):
        self.progress.setValue(int(percent))
        self.lbl_speed.setText(speed)
        self.lbl_status.setText("Encoding...")

    def mark_completed(self):
        self.progress.setValue(100)
        self.lbl_status.setText("✅ Done")
        self.lbl_status.setStyleSheet("color: #4caf50;")

    def mark_failed(self, error: str = ""):
        self.lbl_status.setText("❌ Failed")
        self.lbl_status.setStyleSheet("color: #f44336;")
        self.lbl_status.setToolTip(error)


class QueuePanel(QWidget):
    """Dedicated job queue panel — shows all active and completed jobs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("queuePanel")
        self._job_widgets: dict[str, JobItem] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ─── Header ─────────────────────────────────────────
        header_row = QHBoxLayout()
        header = QLabel("📋  Job Queue")
        header.setObjectName("panelHeader")
        header_row.addWidget(header)

        self.lbl_count = QLabel("0 jobs")
        self.lbl_count.setObjectName("fileCount")
        header_row.addStretch()
        header_row.addWidget(self.lbl_count)

        self.btn_clear_done = QPushButton("🗑 Clear Completed")
        self.btn_clear_done.setObjectName("actionBtn")
        self.btn_clear_done.setFixedHeight(30)
        self.btn_clear_done.clicked.connect(self._clear_completed)
        header_row.addWidget(self.btn_clear_done)

        layout.addLayout(header_row)

        # ─── Job List (Scrollable) ──────────────────────────
        self.job_list_layout = QVBoxLayout()
        self.job_list_layout.setSpacing(6)
        self.job_list_layout.setAlignment(Qt.AlignTop)

        queue_widget = QWidget()
        queue_widget.setLayout(self.job_list_layout)

        queue_scroll = QScrollArea()
        queue_scroll.setWidgetResizable(True)
        queue_scroll.setWidget(queue_widget)

        layout.addWidget(queue_scroll, 1)

        # ─── Empty State ────────────────────────────────────
        self.lbl_empty = QLabel("No jobs in queue.\n\nStart a transcode or conversion to see jobs here.")
        self.lbl_empty.setObjectName("videoPlaceholder")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.job_list_layout.addWidget(self.lbl_empty)

    def add_job(self, job_id: str, filename: str, preset_name: str) -> JobItem:
        """Add a new job widget and return it."""
        self.lbl_empty.hide()
        widget = JobItem(job_id, filename, preset_name)
        self._job_widgets[job_id] = widget
        self.job_list_layout.addWidget(widget)
        self._update_count()
        return widget

    def on_job_progress(self, job_id: str, percent: float, speed: str):
        widget = self._job_widgets.get(job_id)
        if widget:
            widget.update_progress(percent, speed)

    def on_job_completed(self, job_id: str):
        widget = self._job_widgets.get(job_id)
        if widget:
            widget.mark_completed()

    def on_job_failed(self, job_id: str, error: str):
        widget = self._job_widgets.get(job_id)
        if widget:
            widget.mark_failed(error)

    def _clear_completed(self):
        """Remove all completed/failed job widgets."""
        to_remove = []
        for job_id, widget in self._job_widgets.items():
            status = widget.lbl_status.text()
            if "Done" in status or "Failed" in status:
                to_remove.append(job_id)

        for job_id in to_remove:
            widget = self._job_widgets.pop(job_id)
            self.job_list_layout.removeWidget(widget)
            widget.deleteLater()

        self._update_count()
        if not self._job_widgets:
            self.lbl_empty.show()

    def _update_count(self):
        n = len(self._job_widgets)
        self.lbl_count.setText(f"{n} job{'s' if n != 1 else ''}")
