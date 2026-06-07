"""Plugin Manager Integration - Helper functions for integrating plugin manager into main window."""

from PySide6.QtWidgets import QDialog, QVBoxLayout
from src.ui.plugin_manager import PluginManagerWidget
from src.core.logger import get_logger


def show_plugin_manager_dialog(parent):
    """Show plugin manager dialog as a standalone window."""
    logger = get_logger('plugin_integration')
    
    try:
        # Create dialog with plugin manager
        dialog = QDialog(parent)
        dialog.setWindowTitle("Plugin Manager")
        dialog.setFixedSize(800, 600)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add plugin manager widget
        manager = PluginManagerWidget(dialog)
        layout.addWidget(manager)
        
        # Show dialog
        dialog.show()
        
        logger.info("Plugin manager dialog opened")
        
    except Exception as e:
        logger.error(f"Failed to open plugin manager: {e}")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(parent, "Error", f"Failed to open plugin manager: {e}")


def create_plugin_manager(main_window):
    """Create and configure plugin manager for main window."""
    logger = get_logger('plugin_integration')
    
    try:
        from src.core.plugin_system import PluginManager
        
        # Create plugin manager
        manager = PluginManager()
        
        # Set main window reference
        manager.set_main_window(main_window)
        
        # Discover plugins
        manager.discover_plugins()
        
        logger.info("Plugin manager created and configured")
        return manager
        
    except Exception as e:
        logger.error(f"Failed to create plugin manager: {e}")
        return None


def initialize_plugin_system(main_window):
    """Initialize the complete plugin system."""
    logger = get_logger('plugin_integration')
    
    try:
        # Create plugin manager
        manager = create_plugin_manager(main_window)
        
        if manager:
            # Store reference in main window
            main_window.plugin_manager = manager
            
            # Load plugins automatically (optional - can be made configurable)
            # manager.load_all_plugins()
            
            logger.info("Plugin system initialized successfully")
            return True
        else:
            logger.error("Failed to create plugin manager")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize plugin system: {e}")
        return False


def cleanup_plugin_system(main_window):
    """Cleanup the plugin system."""
    logger = get_logger('plugin_integration')
    
    try:
        if hasattr(main_window, 'plugin_manager'):
            main_window.plugin_manager.cleanup()
            delattr(main_window, 'plugin_manager')
            
            logger.info("Plugin system cleaned up successfully")
        
    except Exception as e:
        logger.error(f"Failed to cleanup plugin system: {e}")
