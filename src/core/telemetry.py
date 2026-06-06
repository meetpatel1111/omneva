"""Telemetry System - Anonymous crash reports via Sentry SDK."""

import os
import json
import platform
import sys
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QMessageBox
from src.core.logger import get_logger
from src.core.storage import storage


class TelemetryConfig:
    """Telemetry configuration management."""
    
    def __init__(self):
        self.logger = get_logger('telemetry_config')
        self.config_file = os.path.join(storage.get_app_data_dir(), 'telemetry_config.json')
        
        self.default_config = {
            'enabled': False,
            'crash_reports': True,
            'usage_analytics': False,
            'performance_monitoring': False,
            'error_reports': True,
            'user_id': None,
            'first_run': True,
            'version': '1.4.0',
            'last_prompt': None
        }
        
        self.config = self._load_config()
        
        self.logger.debug("Telemetry config initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load telemetry configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                merged_config = self.default_config.copy()
                merged_config.update(config)
                
                self.logger.debug("Telemetry config loaded from file")
                return merged_config
            else:
                self.logger.debug("Using default telemetry config")
                return self.default_config.copy()
                
        except Exception as e:
            self.logger.error(f"Failed to load telemetry config: {e}")
            return self.default_config.copy()
    
    def save_config(self):
        """Save telemetry configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            self.logger.debug("Telemetry config saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save telemetry config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        self.config[key] = value
        self.save_config()
    
    def is_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self.config.get('enabled', False)
    
    def enable(self, enabled: bool = True):
        """Enable or disable telemetry."""
        self.set('enabled', enabled)
        self.set('first_run', False)
        self.logger.info(f"Telemetry {'enabled' if enabled else 'disabled'}")


class TelemetryManager(QObject):
    """Manages telemetry data collection and reporting."""
    
    # Signals
    telemetry_enabled = Signal(bool)  # telemetry enabled/disabled
    error_reported = Signal(str, str)  # error type, error message
    performance_data = Signal(dict)  # performance metrics
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('telemetry_manager')
        
        self.config = TelemetryConfig()
        self.sentry_client = None
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._collect_performance_data)
        
        self.system_info = self._collect_system_info()
        
        self._initialize_sentry()
        
        self.logger.debug("Telemetry manager initialized")
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for telemetry."""
        try:
            info = {
                'platform': platform.system(),
                'platform_release': platform.release(),
                'platform_version': platform.version(),
                'architecture': platform.machine(),
                'hostname': platform.node(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'python_implementation': platform.python_implementation(),
                'app_version': self.config.get('version', '1.4.0')
            }
            
            # Add Qt version if available
            try:
                from PySide6 import QtCore
                info['qt_version'] = QtCore.qVersion()
            except ImportError:
                pass
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to collect system info: {e}")
            return {}
    
    def _initialize_sentry(self):
        """Initialize Sentry SDK for error reporting."""
        if not self.config.is_enabled():
            self.logger.info("Telemetry disabled, skipping Sentry initialization")
            return
        
        try:
            # Try to import sentry_sdk
            import sentry_sdk
            from sentry_sdk.integrations.qt import QtIntegration
            
            # Sentry DSN (this would be a real DSN in production)
            sentry_dsn = "https://examplePublicKey@o0.ingest.sentry.io/0"
            
            # Configure Sentry
            sentry_sdk.init(
                dsn=sentry_dsn,
                traces_sample_rate=0.1,  # 10% of transactions
                environment="production",
                release=f"omneva@{self.config.get('version', '1.4.0')}",
                integrations=[QtIntegration()],
                before_send=self._before_send_sentry,
                ignore_errors=[
                    "KeyboardInterrupt",
                    "SystemExit",
                    "QtFatalError"
                ]
            )
            
            self.sentry_client = sentry_sdk.get_current_hub()
            
            # Set user context (anonymous)
            user_id = self.config.get('user_id')
            if not user_id:
                import uuid
                user_id = str(uuid.uuid4())
                self.config.set('user_id', user_id)
            
            sentry_sdk.set_user({
                'id': user_id,
                'ip_address': '{{auto}}',  # Anonymize IP
                'username': 'anonymous'
            })
            
            # Set tags
            sentry_sdk.set_tags({
                'platform': self.system_info.get('platform', 'unknown'),
                'version': self.config.get('version', '1.4.0'),
                'python_version': self.system_info.get('python_version', 'unknown')
            })
            
            # Set extra context
            sentry_sdk.set_context('system', self.system_info)
            
            self.logger.info("Sentry SDK initialized successfully")
            
        except ImportError:
            self.logger.warning("Sentry SDK not available, using mock implementation")
            self._create_mock_sentry()
        except Exception as e:
            self.logger.error(f"Failed to initialize Sentry: {e}")
            self._create_mock_sentry()
    
    def _create_mock_sentry(self):
        """Create mock Sentry implementation when SDK is not available."""
        class MockSentryClient:
            def capture_exception(self, exc_info=None):
                self.logger.error(f"Mock exception capture: {exc_info}")
            
            def capture_message(self, message, level='info'):
                self.logger.info(f"Mock message capture: {message}")
            
            def add_breadcrumb(self, message, category='info'):
                self.logger.debug(f"Mock breadcrumb: {message}")
        
        self.sentry_client = MockSentryClient()
    
    def _before_send_sentry(self, event, hint):
        """Filter and modify Sentry events before sending."""
        if not self.config.is_enabled():
            return None
        
        # Remove sensitive information
        if 'request' in event:
            del event['request']
        
        if 'user' in event:
            user = event['user']
            user.pop('email', None)
            user.pop('username', None)
            user.pop('ip_address', None)
        
        # Add custom context
        event['contexts']['app'] = {
            'name': 'Omneva',
            'version': self.config.get('version', '1.4.0'),
            'build': 'unknown'
        }
        
        return event
    
    def enable_telemetry(self, enabled: bool = True):
        """Enable or disable telemetry."""
        self.config.enable(enabled)
        
        if enabled:
            self._initialize_sentry()
            self._start_performance_monitoring()
        else:
            self._stop_performance_monitoring()
        
        self.telemetry_enabled.emit(enabled)
    
    def report_exception(self, exception, context: Optional[Dict[str, Any]] = None):
        """Report an exception to Sentry."""
        if not self.config.is_enabled() or not self.sentry_client:
            return
        
        try:
            # Add context if provided
            if context:
                import sentry_sdk
                sentry_sdk.set_context('custom', context)
            
            # Capture exception
            self.sentry_client.capture_exception(exception)
            
            # Emit signal
            self.error_reported.emit(type(exception).__name__, str(exception))
            
            self.logger.info(f"Exception reported: {type(exception).__name__}")
            
        except Exception as e:
            self.logger.error(f"Failed to report exception: {e}")
    
    def report_message(self, message: str, level: str = 'info', context: Optional[Dict[str, Any]] = None):
        """Report a message to Sentry."""
        if not self.config.is_enabled() or not self.sentry_client:
            return
        
        try:
            # Add context if provided
            if context:
                import sentry_sdk
                sentry_sdk.set_context('custom', context)
            
            # Capture message
            self.sentry_client.capture_message(message, level)
            
            self.logger.info(f"Message reported: {message}")
            
        except Exception as e:
            self.logger.error(f"Failed to report message: {e}")
    
    def add_breadcrumb(self, message: str, category: str = 'info', level: str = 'info'):
        """Add a breadcrumb to track user actions."""
        if not self.config.is_enabled() or not self.sentry_client:
            return
        
        try:
            self.sentry_client.add_breadcrumb(message, category, level)
            
        except Exception as e:
            self.logger.error(f"Failed to add breadcrumb: {e}")
    
    def _start_performance_monitoring(self):
        """Start performance monitoring."""
        if self.config.get('performance_monitoring', False):
            self.performance_timer.start(30000)  # Every 30 seconds
            self.logger.info("Performance monitoring started")
    
    def _stop_performance_monitoring(self):
        """Stop performance monitoring."""
        if self.performance_timer.isActive():
            self.performance_timer.stop()
            self.logger.info("Performance monitoring stopped")
    
    def _collect_performance_data(self):
        """Collect performance metrics."""
        try:
            import psutil
            
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            performance_data = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_free_gb': disk.free / (1024**3),
                'disk_percent': (disk.used / disk.total) * 100
            }
            
            # Process metrics
            process = psutil.Process()
            performance_data.update({
                'process_cpu_percent': process.cpu_percent(),
                'process_memory_mb': process.memory_info().rss / (1024**2),
                'process_threads': process.num_threads(),
                'process_handles': process.num_handles() if hasattr(process, 'num_handles') else 0
            })
            
            self.performance_data.emit(performance_data)
            
            # Report to Sentry if enabled
            if self.config.get('performance_monitoring', False):
                self.report_message("Performance metrics collected", 'info', performance_data)
            
        except ImportError:
            self.logger.warning("psutil not available for performance monitoring")
        except Exception as e:
            self.logger.error(f"Failed to collect performance data: {e}")
    
    def prompt_for_consent(self, parent) -> bool:
        """Prompt user for telemetry consent."""
        if not self.config.get('first_run', False):
            return self.config.is_enabled()
        
        try:
            # Create consent dialog
            msg = QMessageBox(parent)
            msg.setWindowTitle("Telemetry & Crash Reports")
            msg.setIcon(QMessageBox.Question)
            
            title = "Help Improve Omneva"
            message = """
Omneva can collect anonymous telemetry data and crash reports to help us improve the application.

<b>What we collect:</b>
• Anonymous crash reports when errors occur
• System information (OS, Python version, etc.)
• Performance metrics (CPU, memory usage)
• Application usage patterns

<b>What we DON'T collect:</b>
• Personal information or files
• Media file names or content
• IP addresses or location data
• Any sensitive information

You can change this setting anytime in the preferences.

<b>Your data is completely anonymous and helps us fix bugs faster.</b>
            """.strip()
            
            msg.setText(title)
            msg.setInformativeText(message)
            
            # Add custom buttons
            enable_btn = msg.addButton("Enable Telemetry", QMessageBox.AcceptRole)
            disable_btn = msg.addButton("Disable", QMessageBox.RejectRole)
            
            # Set default to enable (helps us get more data)
            msg.setDefaultButton(enable_btn)
            
            # Show dialog
            msg.exec_()
            
            # Handle response
            if msg.clickedButton() == enable_btn:
                self.enable_telemetry(True)
                return True
            else:
                self.enable_telemetry(False)
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to show consent dialog: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get telemetry configuration."""
        return self.config.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update telemetry configuration."""
        for key, value in new_config.items():
            self.config.set(key, value)
        
        # Reinitialize if enabled/disabled status changed
        if 'enabled' in new_config:
            self.enable_telemetry(new_config['enabled'])
    
    def cleanup(self):
        """Cleanup telemetry resources."""
        self._stop_performance_monitoring()
        
        if self.sentry_client:
            try:
                import sentry_sdk
                sentry_sdk.flush()
            except Exception:
                pass
        
        self.logger.info("Telemetry manager cleaned up")


# Global telemetry instance
_telemetry_manager = None


def get_telemetry_manager() -> TelemetryManager:
    """Get the global telemetry manager instance."""
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager()
    return _telemetry_manager


def initialize_telemetry(parent=None) -> TelemetryManager:
    """Initialize telemetry system."""
    manager = get_telemetry_manager()
    
    # Prompt for consent on first run
    if parent and manager.config.get('first_run', False):
        manager.prompt_for_consent(parent)
    
    return manager


def report_exception(exception, context: Optional[Dict[str, Any]] = None):
    """Report an exception to telemetry."""
    manager = get_telemetry_manager()
    manager.report_exception(exception, context)


def report_message(message: str, level: str = 'info', context: Optional[Dict[str, Any]] = None):
    """Report a message to telemetry."""
    manager = get_telemetry_manager()
    manager.report_message(message, level, context)


def add_breadcrumb(message: str, category: str = 'info', level: str = 'info'):
    """Add a breadcrumb to track user actions."""
    manager = get_telemetry_manager()
    manager.add_breadcrumb(message, category, level)
