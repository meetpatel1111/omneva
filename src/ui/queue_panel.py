"""Queue Panel — Dedicated job queue view for all transcoding/conversion jobs."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QScrollArea, QCheckBox
)
from PySide6.QtCore import Qt
from src.core.logger import get_logger
from src.core.recovery_service import get_recovery_service


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
        self.lbl_speed.setAlignment(Qt.AlignmentFlag.AlignRight)

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
        self.logger = get_logger('queue_panel')
        self.recovery_service = get_recovery_service()
        self._job_widgets: dict[str, JobItem] = {}
        self._setup_ui()
        
        # Setup autosave timer for queue state
        self._setup_autosave()

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

        # Post-encode actions
        self.chk_shutdown = QCheckBox("Shutdown PC when done")
        self.chk_shutdown.setObjectName("postEncodeAction")
        self.chk_shutdown.setToolTip("Automatically shutdown the computer when all jobs complete")
        self.chk_shutdown.setStyleSheet("""
            QCheckBox {
                color: #fff;
                font-size: 11px;
                padding: 4px 8px;
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #3a3a3a;
            }
            QCheckBox:hover {
                background-color: #4a4a4a;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #888;
                border-radius: 2px;
                background-color: #2a2a2a;
            }
            QCheckBox::indicator:checked {
                background-color: #ff6b6b;
                border-color: #ff6b6b;
            }
            QCheckBox::indicator:checked::after {
                content: "✓";
                color: white;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        header_row.addWidget(self.chk_shutdown)

        self.chk_sound = QCheckBox("Play sound when done")
        self.chk_sound.setObjectName("postEncodeAction")
        self.chk_sound.setToolTip("Play a notification sound when all jobs complete")
        self.chk_sound.setStyleSheet("""
            QCheckBox {
                color: #fff;
                font-size: 11px;
                padding: 4px 8px;
                border: 1px solid #555;
                border-radius: 4px;
                background-color: #3a3a3a;
            }
            QCheckBox:hover {
                background-color: #4a4a4a;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #888;
                border-radius: 2px;
                background-color: #2a2a2a;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            QCheckBox::indicator:checked::after {
                content: "✓";
                color: white;
                font-size: 10px;
                font-weight: bold;
            }
        """)
        header_row.addWidget(self.chk_sound)

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
            
        # Autosave after clearing completed jobs
        self._autosave_state()

    def _update_count(self):
        n = len(self._job_widgets)
        self.lbl_count.setText(f"{n} job{'s' if n != 1 else ''}")

    def _setup_autosave(self):
        """Setup autosave timer for queue state."""
        from PySide6.QtCore import QTimer
        
        # Autosave every 5 minutes
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave_state)
        self._autosave_timer.start(300000)  # 5 minutes in milliseconds

    def _autosave_state(self):
        """Save current queue state for crash recovery."""
        try:
            current_state = {
                'queue_jobs': self._get_job_states(),
                'job_count': len(self._job_widgets)
            }
            
            self.recovery_service.autosave_if_needed(current_state)
            
        except Exception as e:
            self.logger.error(f"Queue autosave failed: {e}")

    def _get_job_states(self):
        """Get current job states for recovery."""
        job_states = []
        try:
            for job_id, widget in self._job_widgets.items():
                job_states.append({
                    'id': job_id,
                    'filename': widget.lbl_name.text().replace('📄 ', ''),
                    'preset': widget.lbl_preset.text(),
                    'status': widget.lbl_status.text(),
                    'progress': widget.progress_bar.value(),
                    'completed': widget.is_completed()
                })
        except Exception as e:
            self.logger.error(f"Failed to get queue job states: {e}")
        return job_states

    def get_post_encode_actions(self) -> dict:
        """Get the current post-encode action settings."""
        return {
            "shutdown": self.chk_shutdown.isChecked(),
            "sound": self.chk_sound.isChecked()
        }
