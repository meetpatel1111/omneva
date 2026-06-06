"""Patch file for adding plugin system integration to main window.

This file contains the code that should be added to main_window.py
to integrate the plugin system feature.
"""

# Add this import to the imports section in main_window.py:
# from src.ui.plugin_integration import show_plugin_manager_dialog, initialize_plugin_system, cleanup_plugin_system

# Add this to the MainWindow.__init__ method after other initializations:
# initialize_plugin_system(self)

# Add this signal connection in _connect_signals method:
# self.act_plugin_manager.triggered.connect(self._show_plugin_manager)

# Add this method to MainWindow class:
def _show_plugin_manager(self):
    """Show plugin manager dialog."""
    from src.ui.plugin_integration import show_plugin_manager_dialog
    show_plugin_manager_dialog(self)

# Add this to the closeEvent method in MainWindow class (before event.accept()):
# cleanup_plugin_system(self)
