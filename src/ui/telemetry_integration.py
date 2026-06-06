"""Telemetry Integration - Helper functions for integrating telemetry into main window."""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, Signal
from src.ui.telemetry_settings import TelemetrySettingsWidget
from src.core.telemetry import initialize_telemetry, get_telemetry_manager
from src.core.logger import get_logger


def show_telemetry_settings_dialog(parent):
    """Show telemetry settings dialog as a standalone window."""
    logger = get_logger('telemetry_integration')
    
    try:
        # Create dialog
        dialog = QDialog(parent)
        dialog.setWindowTitle("Telemetry Settings")
        dialog.setFixedSize(600, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Add settings widget
        settings = TelemetrySettingsWidget()
        layout.addWidget(settings)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6200ea;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #7c4dff;
            }
        """)
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        dialog.exec_()
        
        logger.info("Telemetry settings dialog opened")
        
    except Exception as e:
        logger.error(f"Failed to open telemetry settings: {e}")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(parent, "Error", f"Failed to open telemetry settings: {e}")


def initialize_telemetry_system(main_window):
    """Initialize the complete telemetry system."""
    logger = get_logger('telemetry_integration')
    
    try:
        # Initialize telemetry
        manager = initialize_telemetry(main_window)
        
        if manager:
            # Store reference in main window
            main_window.telemetry_manager = manager
            
            # Connect signals
            manager.telemetry_enabled.connect(lambda enabled: _on_telemetry_enabled(main_window, enabled))
            manager.error_reported.connect(lambda error_type, message: _on_error_reported(main_window, error_type, message))
            
            # Add breadcrumb for application start
            manager.add_breadcrumb("Application started", "app", "info")
            
            logger.info("Telemetry system initialized successfully")
            return True
        else:
            logger.error("Failed to initialize telemetry manager")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize telemetry system: {e}")
        return False


def _on_telemetry_enabled(main_window, enabled):
    """Handle telemetry enabled/disabled."""
    logger = get_logger('telemetry_integration')
    
    try:
        manager = get_telemetry_manager()
        
        if enabled:
            logger.info("Telemetry enabled by user")
            manager.add_breadcrumb("Telemetry enabled", "settings", "info")
        else:
            logger.info("Telemetry disabled by user")
            manager.add_breadcrumb("Telemetry disabled", "settings", "info")
            
    except Exception as e:
        logger.error(f"Failed to handle telemetry enabled change: {e}")


def _on_error_reported(main_window, error_type, message):
    """Handle error reported to telemetry."""
    logger = get_logger('telemetry_integration')
    
    try:
        logger.info(f"Error reported to telemetry: {error_type} - {message}")
        
        # Could show a notification to the user here if desired
        # For now, just log it
        
    except Exception as e:
        logger.error(f"Failed to handle error reported: {e}")


def setup_exception_handler(main_window):
    """Setup global exception handler for telemetry."""
    logger = get_logger('telemetry_integration')
    
    try:
        import sys
        
        def handle_exception(exc_type, exc_value, exc_traceback):
            """Global exception handler."""
            logger.error(f"Unhandled exception: {exc_type.__name__}: {exc_value}")
            
            # Report to telemetry
            manager = get_telemetry_manager()
            if manager and manager.config.is_enabled():
                context = {
                    'unhandled': True,
                    'exc_type': exc_type.__name__,
                    'exc_value': str(exc_value),
                    'thread': 'main'
                }
                manager.report_exception(exc_value, context)
            
            # Call original handler
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        
        # Install exception handler
        sys.excepthook = handle_exception
        
        logger.info("Global exception handler installed")
        
    except Exception as e:
        logger.error(f"Failed to setup exception handler: {e}")


def cleanup_telemetry_system(main_window):
    """Cleanup the telemetry system."""
    logger = get_logger('telemetry_integration')
    
    try:
        if hasattr(main_window, 'telemetry_manager'):
            # Add breadcrumb for application shutdown
            main_window.telemetry_manager.add_breadcrumb("Application shutting down", "app", "info")
            
            # Cleanup
            main_window.telemetry_manager.cleanup()
            delattr(main_window, 'telemetry_manager')
            
            logger.info("Telemetry system cleaned up successfully")
        
    except Exception as e:
        logger.error(f"Failed to cleanup telemetry system: {e}")


def track_user_action(action_name, category='user', data=None):
    """Track a user action for telemetry."""
    try:
        manager = get_telemetry_manager()
        if manager and manager.config.is_enabled():
            
            # Add breadcrumb
            manager.add_breadcrumb(action_name, category, 'info')
            
            # Report message if usage analytics is enabled
            if manager.config.get('usage_analytics', False):
                context = {
                    'action': action_name,
                    'category': category,
                    'data': data or {}
                }
                manager.report_message(f"User action: {action_name}", 'info', context)
                
    except Exception as e:
        logger = get_logger('telemetry_integration')
        logger.error(f"Failed to track user action: {e}")


def track_media_event(event_name, file_path=None, metadata=None):
    """Track a media-related event for telemetry."""
    try:
        manager = get_telemetry_manager()
        if manager and manager.config.is_enabled():
            
            # Add breadcrumb
            manager.add_breadcrumb(f"Media: {event_name}", 'media', 'info')
            
            # Report message if usage analytics is enabled
            if manager.config.get('usage_analytics', False):
                context = {
                    'event': event_name,
                    'file_path': file_path,
                    'metadata': metadata or {}
                }
                manager.report_message(f"Media event: {event_name}", 'info', context)
                
    except Exception as e:
        logger = get_logger('telemetry_integration')
        logger.error(f"Failed to track media event: {e}")


def track_performance_event(event_name, metrics=None):
    """Track a performance-related event for telemetry."""
    try:
        manager = get_telemetry_manager()
        if manager and manager.config.is_enabled():
            
            # Add breadcrumb
            manager.add_breadcrumb(f"Performance: {event_name}", 'performance', 'info')
            
            # Report message if performance monitoring is enabled
            if manager.config.get('performance_monitoring', False):
                context = {
                    'event': event_name,
                    'metrics': metrics or {}
                }
                manager.report_message(f"Performance event: {event_name}", 'info', context)
                
    except Exception as e:
        logger = get_logger('telemetry_integration')
        logger.error(f"Failed to track performance event: {e}")
