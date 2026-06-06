"""Patch file for adding keyboard navigation integration to main window.

This file contains the code that should be added to main_window.py
to integrate the keyboard navigation feature.
"""

# Add this import to the imports section in main_window.py:
# from src.ui.keyboard_integration import create_keyboard_navigation_manager, show_keyboard_navigation_settings

# Add this to the MainWindow.__init__ method after other initializations:
# self.keyboard_nav_manager = create_keyboard_navigation_manager(self)

# Add this signal connection in _connect_signals method:
# self.act_keyboard_navigation.triggered.connect(self._toggle_keyboard_navigation)

# Add this method to MainWindow class:
def _toggle_keyboard_navigation(self):
    """Toggle keyboard navigation mode."""
    if self.keyboard_nav_manager:
        enabled = self.act_keyboard_navigation.isChecked()
        self.keyboard_nav_manager.enable_keyboard_mode(enabled)
        
        if enabled:
            from src.core.logger import get_logger
            logger = get_logger('main_window')
            logger.info("Keyboard navigation mode enabled")
        else:
            from src.core.logger import get_logger
            logger = get_logger('main_window')
            logger.info("Keyboard navigation mode disabled")
