"""Telemetry Settings UI - Interface for configuring telemetry and crash reports."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QGroupBox, QMessageBox, QFileDialog, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QProgressBar, QCheckBox, QFrame, QSplitter, QToolButton,
    QMenu, QAction, QListWidget, QListWidgetItem, QDialog,
    QDialogButtonBox, QTabWidget, QScrollArea, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QPixmap, QFont
from src.core.logger import get_logger
from src.core.telemetry import get_telemetry_manager, TelemetryConfig


class TelemetrySettingsWidget(QWidget):
    """Widget for configuring telemetry settings."""
    
    settings_changed = Signal(dict)  # settings dictionary
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('telemetry_settings')
        
        self.telemetry_manager = get_telemetry_manager()
        
        self._setup_ui()
        self._load_settings()
        
        self.logger.debug("Telemetry settings widget initialized")
    
    def _setup_ui(self):
        """Setup the telemetry settings UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header_label = QLabel("Telemetry & Crash Reports")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                padding: 8px;
            }
        """)
        layout.addWidget(header_label)
        
        # Main telemetry settings
        main_group = QGroupBox("Telemetry Settings")
        main_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        
        main_layout = QVBoxLayout()
        
        # Enable telemetry
        self.enable_cb = QCheckBox("Enable Telemetry & Crash Reports")
        self.enable_cb.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 11px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #555555;
                border-radius: 3px;
                background-color: #3a3a3a;
            }
            QCheckBox::indicator:checked {
                background-color: #6200ea;
                border-color: #6200ea;
            }
        """)
        self.enable_cb.toggled.connect(self._on_settings_changed)
        main_layout.addWidget(self.enable_cb)
        
        # Telemetry options
        options_layout = QVBoxLayout()
        
        self.crash_reports_cb = QCheckBox("Send Crash Reports")
        self.crash_reports_cb.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-size: 10px;
                spacing: 6px;
                margin-left: 20px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #555555;
                border-radius: 2px;
                background-color: #3a3a3a;
            }
            QCheckBox::indicator:checked {
                background-color: #4caf50;
                border-color: #4caf50;
            }
        """)
        self.crash_reports_cb.toggled.connect(self._on_settings_changed)
        options_layout.addWidget(self.crash_reports_cb)
        
        self.error_reports_cb = QCheckBox("Send Error Reports")
        self.error_reports_cb.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-size: 10px;
                spacing: 6px;
                margin-left: 20px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #555555;
                border-radius: 2px;
                background-color: #3a3a3a;
            }
            QCheckBox::indicator:checked {
                background-color: #4caf50;
                border-color: #4caf50;
            }
        """)
        self.error_reports_cb.toggled.connect(self._on_settings_changed)
        options_layout.addWidget(self.error_reports_cb)
        
        self.usage_analytics_cb = QCheckBox("Send Usage Analytics")
        self.usage_analytics_cb.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-size: 10px;
                spacing: 6px;
                margin-left: 20px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #555555;
                border-radius: 2px;
                background-color: #3a3a3a;
            }
            QCheckBox::indicator:checked {
                background-color: #4caf50;
                border-color: #4caf50;
            }
        """)
        self.usage_analytics_cb.toggled.connect(self._on_settings_changed)
        options_layout.addWidget(self.usage_analytics_cb)
        
        self.performance_monitoring_cb = QCheckBox("Performance Monitoring")
        self.performance_monitoring_cb.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                font-size: 10px;
                spacing: 6px;
                margin-left: 20px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #555555;
                border-radius: 2px;
                background-color: #3a3a3a;
            }
            QCheckBox::indicator:checked {
                background-color: #4caf50;
                border-color: #4caf50;
            }
        """)
        self.performance_monitoring_cb.toggled.connect(self._on_settings_changed)
        options_layout.addWidget(self.performance_monitoring_cb)
        
        main_layout.addLayout(options_layout)
        main_group.setLayout(main_layout)
        layout.addWidget(main_group)
        
        # Privacy information
        privacy_group = QGroupBox("Privacy Information")
        privacy_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        
        privacy_layout = QVBoxLayout()
        
        privacy_text = QTextEdit()
        privacy_text.setMaximumHeight(120)
        privacy_text.setReadOnly(True)
        privacy_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                font-size: 9px;
                line-height: 1.4;
            }
        """)
        privacy_text.setPlainText("""
<b>What we collect:</b>
• Anonymous crash reports when errors occur
• System information (OS, Python version, hardware specs)
• Performance metrics (CPU, memory usage)
• Application usage patterns and feature usage

<b>What we DON'T collect:</b>
• Personal information or identifiable data
• Media file names, paths, or content
• IP addresses or location data
• Any sensitive or private information

<b>Data Security:</b>
• All data is anonymized before sending
• Data is encrypted in transit
• Data is used only for improving the application
• You can opt-out at any time

<b>Your Rights:</b>
• You can disable telemetry at any time
• You can request data deletion
• You can view what data is collected
• You have full control over your privacy
        """.strip())
        privacy_layout.addWidget(privacy_text)
        
        privacy_group.setLayout(privacy_layout)
        layout.addWidget(privacy_group)
        
        # Status information
        status_group = QGroupBox("Status")
        status_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px 0 4px;
            }
        """)
        
        status_layout = QVBoxLayout()
        
        # Current status
        status_info_layout = QHBoxLayout()
        status_info_layout.addWidget(QLabel("Status:"))
        
        self.status_label = QLabel("Disabled")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #f44336;
                font-weight: bold;
                font-size: 10px;
            }
        """)
        status_info_layout.addWidget(self.status_label)
        status_info_layout.addStretch()
        
        status_layout.addLayout(status_info_layout)
        
        # User ID
        user_info_layout = QHBoxLayout()
        user_info_layout.addWidget(QLabel("User ID:"))
        
        self.user_id_label = QLabel("Not generated")
        self.user_id_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-family: 'Consolas', monospace;
                font-size: 9px;
            }
        """)
        user_info_layout.addWidget(self.user_id_label)
        user_info_layout.addStretch()
        
        status_layout.addLayout(user_info_layout)
        
        # Test buttons
        test_layout = QHBoxLayout()
        
        self.test_error_btn = QPushButton("Test Error Report")
        self.test_error_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #ffa726;
            }
        """)
        self.test_error_btn.clicked.connect(self._test_error_report)
        test_layout.addWidget(self.test_error_btn)
        
        self.test_message_btn = QPushButton("Test Message")
        self.test_message_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #42a5f5;
            }
        """)
        self.test_message_btn.clicked.connect(self._test_message)
        test_layout.addWidget(self.test_message_btn)
        
        test_layout.addStretch()
        status_layout.addLayout(test_layout)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addStretch()
        
        # Set dark theme
        self.setStyleSheet("""
            TelemetrySettingsWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
    
    def _load_settings(self):
        """Load current telemetry settings."""
        try:
            config = self.telemetry_manager.get_config()
            
            self.enable_cb.setChecked(config.get('enabled', False))
            self.crash_reports_cb.setChecked(config.get('crash_reports', True))
            self.error_reports_cb.setChecked(config.get('error_reports', True))
            self.usage_analytics_cb.setChecked(config.get('usage_analytics', False))
            self.performance_monitoring_cb.setChecked(config.get('performance_monitoring', False))
            
            # Update status
            self._update_status_display()
            
            # Update user ID
            user_id = config.get('user_id')
            if user_id:
                self.user_id_label.setText(user_id[:8] + "...")
            else:
                self.user_id_label.setText("Not generated")
            
            # Enable/disable options based on main setting
            self._update_option_states()
            
        except Exception as e:
            self.logger.error(f"Failed to load telemetry settings: {e}")
    
    def _update_status_display(self):
        """Update the status display."""
        if self.telemetry_manager.config.is_enabled():
            self.status_label.setText("Enabled")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #4caf50;
                    font-weight: bold;
                    font-size: 10px;
                }
            """)
        else:
            self.status_label.setText("Disabled")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #f44336;
                    font-weight: bold;
                    font-size: 10px;
                }
            """)
    
    def _update_option_states(self):
        """Enable/disable option checkboxes based on main setting."""
        enabled = self.enable_cb.isChecked()
        
        self.crash_reports_cb.setEnabled(enabled)
        self.error_reports_cb.setEnabled(enabled)
        self.usage_analytics_cb.setEnabled(enabled)
        self.performance_monitoring_cb.setEnabled(enabled)
        
        self.test_error_btn.setEnabled(enabled)
        self.test_message_btn.setEnabled(enabled)
    
    def _on_settings_changed(self):
        """Handle settings changes."""
        settings = {
            'enabled': self.enable_cb.isChecked(),
            'crash_reports': self.crash_reports_cb.isChecked(),
            'error_reports': self.error_reports_cb.isChecked(),
            'usage_analytics': self.usage_analytics_cb.isChecked(),
            'performance_monitoring': self.performance_monitoring_cb.isChecked()
        }
        
        # Update telemetry manager
        self.telemetry_manager.update_config(settings)
        
        # Update display
        self._update_status_display()
        self._update_option_states()
        
        # Emit signal
        self.settings_changed.emit(settings)
    
    def _test_error_report(self):
        """Test error reporting."""
        try:
            # Create a test exception
            test_exception = Exception("This is a test error for telemetry reporting")
            
            # Add context
            context = {
                'test': True,
                'source': 'telemetry_settings',
                'timestamp': 'test_timestamp'
            }
            
            # Report the exception
            self.telemetry_manager.report_exception(test_exception, context)
            
            QMessageBox.information(self, "Test Error", 
                                      "Test error report sent successfully!\n"
                                      "Check your Sentry dashboard to see the report.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                                f"Failed to send test error: {e}")
    
    def _test_message(self):
        """Test message reporting."""
        try:
            # Add context
            context = {
                'test': True,
                'source': 'telemetry_settings',
                'timestamp': 'test_timestamp'
            }
            
            # Report the message
            self.telemetry_manager.report_message("This is a test message for telemetry reporting", 'info', context)
            
            QMessageBox.information(self, "Test Message", 
                                      "Test message sent successfully!\n"
                                      "Check your Sentry dashboard to see the message.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                                f"Failed to send test message: {e}")
    
    def get_settings(self):
        """Get current settings."""
        return {
            'enabled': self.enable_cb.isChecked(),
            'crash_reports': self.crash_reports_cb.isChecked(),
            'error_reports': self.error_reports_cb.isChecked(),
            'usage_analytics': self.usage_analytics_cb.isChecked(),
            'performance_monitoring': self.performance_monitoring_cb.isChecked()
        }
    
    def set_settings(self, settings):
        """Set settings from dictionary."""
        self.enable_cb.setChecked(settings.get('enabled', False))
        self.crash_reports_cb.setChecked(settings.get('crash_reports', True))
        self.error_reports_cb.setChecked(settings.get('error_reports', True))
        self.usage_analytics_cb.setChecked(settings.get('usage_analytics', False))
        self.performance_monitoring_cb.setChecked(settings.get('performance_monitoring', False))
        
        self._update_status_display()
        self._update_option_states()


class TelemetrySettingsDialog(QWidget):
    """Dialog wrapper for telemetry settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Telemetry Settings")
        self.setFixedSize(600, 500)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.settings = TelemetrySettingsWidget()
        layout.addWidget(self.settings)
        
        self.setStyleSheet("""
            TelemetrySettingsDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
