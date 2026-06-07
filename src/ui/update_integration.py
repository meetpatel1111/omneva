"""Update System Integration - Helper functions for integrating update system into main window."""

from PySide6.QtWidgets import QMessageBox
from src.core.updater import initialize_updater, get_update_checker, get_update_config
from src.ui.update_dialog import show_update_dialog, show_no_update_dialog
from src.core.logger import get_logger


def initialize_update_system(main_window, current_version: str = "1.4.1"):
    """Initialize the complete update system."""
    logger = get_logger('update_integration')
    
    try:
        # Initialize updater
        checker = initialize_updater(current_version)
        
        if checker:
            # Store reference in main window
            main_window.update_checker = checker
            
            # Connect signals
            checker.update_available.connect(lambda release: _on_update_available(main_window, release))
            checker.no_update_available.connect(lambda: _on_no_update_available(main_window))
            checker.check_failed.connect(lambda error: _on_check_failed(main_window, error))
            
            logger.info("Update system initialized successfully")
            return True
        else:
            logger.error("Failed to initialize update checker")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize update system: {e}")
        return False


def _on_update_available(main_window, release_info):
    """Handle update available signal."""
    logger = get_logger('update_integration')
    
    try:
        # Check if user wants to skip this version
        config = get_update_config()
        skip_version = config.get('skip_version')
        current_version = release_info.get('tag_name', '').lstrip('v')
        
        if skip_version == current_version:
            logger.info(f"User has chosen to skip version {current_version}")
            return
        
        # Show update dialog
        result = show_update_dialog(main_window, release_info)
        
        if result == QMessageBox.Accepted:
            # User downloaded update or closed dialog
            logger.info("Update dialog closed by user")
        else:
            # User chose to be reminded later
            logger.info("User chose to be reminded later")
            
    except Exception as e:
        logger.error(f"Failed to handle update available: {e}")


def _on_no_update_available(main_window):
    """Handle no update available signal."""
    logger = get_logger('update_integration')
    
    try:
        # Show no update dialog
        show_no_update_dialog(main_window)
        
        # Update last check time
        config = get_update_config()
        config.update_last_check()
        
        logger.info("No updates available")
        
    except Exception as e:
        logger.error(f"Failed to handle no update available: {e}")


def _on_check_failed(main_window, error_message):
    """Handle update check failure."""
    logger = get_logger('update_integration')
    
    try:
        # Show error message
        QMessageBox.warning(
            main_window,
            "Update Check Failed",
            f"Failed to check for updates:\n\n{error_message}\n\n"
            "Please check your internet connection and try again later."
        )
        
        logger.error(f"Update check failed: {error_message}")
        
    except Exception as e:
        logger.error(f"Failed to handle check failed: {e}")


def check_for_updates_manually(main_window):
    """Manually check for updates."""
    logger = get_logger('update_integration')
    
    try:
        checker = get_update_checker()
        
        if checker:
            logger.info("Manual update check requested")
            checker.check_for_updates(force=True)
        else:
            QMessageBox.warning(main_window, "Error", "Update system not initialized.")
            
    except Exception as e:
        logger.error(f"Failed to manually check for updates: {e}")
        QMessageBox.critical(main_window, "Error", f"Failed to check for updates: {e}")


def cleanup_update_system(main_window):
    """Cleanup the update system."""
    logger = get_logger('update_integration')
    
    try:
        if hasattr(main_window, 'update_checker'):
            main_window.update_checker.stop_auto_check()
            delattr(main_window, 'update_checker')
            
            logger.info("Update system cleaned up successfully")
        
    except Exception as e:
        logger.error(f"Failed to cleanup update system: {e}")


def get_update_status(main_window) -> dict:
    """Get current update system status."""
    logger = get_logger('update_integration')
    
    try:
        status = {
            'system_initialized': hasattr(main_window, 'update_checker'),
            'auto_check_enabled': False,
            'last_check_time': None,
            'last_check_version': None
        }
        
        if hasattr(main_window, 'update_checker'):
            config = get_update_config()
            status.update({
                'auto_check_enabled': config.get('auto_check_enabled', False),
                'last_check_time': config.get('last_check_time'),
                'last_check_version': config.get('last_check_version'),
                'skip_version': config.get('skip_version'),
                'stable_only': config.get('stable_only', True),
                'beta_updates': config.get('beta_updates', False),
                'prefer_tags': config.get('prefer_tags', False)
            })
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get update status: {e}")
        return {'error': str(e)}


def configure_auto_check(enabled: bool, interval_hours: int = 24):
    """Configure automatic update checking."""
    logger = get_logger('update_integration')
    
    try:
        config = get_update_config()
        config.set('auto_check_enabled', enabled)
        config.set('check_interval_hours', interval_hours)
        
        logger.info(f"Auto-check configured: enabled={enabled}, interval={interval_hours}h")
        
    except Exception as e:
        logger.error(f"Failed to configure auto-check: {e}")


def configure_stable_updates(stable_only: bool = True):
    """Configure whether to check for stable releases only."""
    logger = get_logger('update_integration')
    
    try:
        config = get_update_config()
        config.set('stable_only', stable_only)
        
        if stable_only:
            logger.info("Configured to check for stable releases only")
        else:
            logger.info("Configured to include pre-release updates")
        
    except Exception as e:
        logger.error(f"Failed to configure stable updates: {e}")


def configure_tag_preference(prefer_tags: bool = False):
    """Configure whether to prefer tags over releases."""
    logger = get_logger('update_integration')
    
    try:
        config = get_update_config()
        config.set('prefer_tags', prefer_tags)
        
        if prefer_tags:
            logger.info("Configured to prefer git tags over releases")
        else:
            logger.info("Configured to prefer releases over git tags")
        
    except Exception as e:
        logger.error(f"Failed to configure tag preference: {e}")


def skip_current_version(main_window):
    """Skip the current available version."""
    logger = get_logger('update_integration')
    
    try:
        config = get_update_config()
        current_skip = config.get('skip_version')
        
        if current_skip:
            # Clear current skip
            config.set('skip_version', None)
            logger.info("Cleared version skip")
            return False
        else:
            # This would be called from update dialog when user skips
            logger.info("No version to skip")
            return False
            
    except Exception as e:
        logger.error(f"Failed to skip version: {e}")
        return False
