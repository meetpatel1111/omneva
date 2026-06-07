"""Keyboard Navigation Integration - Helper functions for integrating keyboard navigation into main window."""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QWidget
from src.ui.keyboard_navigation import KeyboardNavigationManager, KeyboardNavigationSettings
from src.core.logger import get_logger


def show_keyboard_navigation_settings(parent):
    """Show keyboard navigation settings dialog."""
    logger = get_logger('keyboard_integration')
    
    try:
        # Create dialog
        dialog = QDialog(parent)
        dialog.setWindowTitle("Keyboard Navigation Settings")
        dialog.setFixedSize(500, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
        
        # Create layout
        layout = QVBoxLayout(dialog)
        
        # Add settings widget
        settings = KeyboardNavigationSettings()
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
        
        logger.info("Keyboard navigation settings dialog opened")
        
    except Exception as e:
        logger.error(f"Failed to open keyboard navigation settings: {e}")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(parent, "Error", f"Failed to open keyboard navigation settings: {e}")


def create_keyboard_navigation_manager(main_window):
    """Create and configure keyboard navigation manager for main window."""
    logger = get_logger('keyboard_integration')
    
    try:
        # Create manager
        manager = KeyboardNavigationManager(main_window)
        
        # Connect signals to main window methods
        manager.vim_command_executed.connect(lambda cmd: _handle_vim_command(main_window, cmd))
        
        logger.info("Keyboard navigation manager created")
        return manager
        
    except Exception as e:
        logger.error(f"Failed to create keyboard navigation manager: {e}")
        return None


def _handle_vim_command(main_window, command):
    """Handle Vim commands and route to appropriate main window methods."""
    logger = get_logger('keyboard_integration')
    
    try:
        # Map Vim commands to main window methods
        command_map = {
            'toggle_playback': lambda: main_window.player_page.vlc.toggle_play_pause(),
            'stop': lambda: main_window.player_page.vlc.stop(),
            'toggle_fullscreen': lambda: main_window.toggle_video_fullscreen(),
            'toggle_mute': lambda: main_window.player_page.vlc.toggle_mute(),
            'open_file': lambda: main_window._open_file(),
            'close': lambda: main_window.close(),
            'activate': lambda: _activate_current_focused(main_window),
            'activate_item': lambda: _activate_current_item(main_window),
            'start_search': lambda: _start_search_mode(main_window),
            'insert_mode': lambda: logger.info("Switched to insert mode"),
            'normal_mode': lambda: logger.info("Switched to normal mode"),
            'visual_mode': lambda: logger.info("Switched to visual mode")
        }
        
        # Handle volume adjustment
        if command.startswith('adjust_volume_'):
            direction = command.split('_')[-1]
            volume_step = 10  # 10% volume steps
            
            if hasattr(main_window.player_page, 'vlc'):
                current_volume = main_window.player_page.vlc.audio_get_volume()
                if direction == '1':  # Up
                    new_volume = min(100, current_volume + volume_step)
                else:  # Down
                    new_volume = max(0, current_volume - volume_step)
                
                main_window.player_page.vlc.audio_set_volume(new_volume)
                logger.info(f"Volume adjusted to {new_volume}%")
            return
        
        # Handle search commands
        if command.startswith('next_search_') or command.startswith('prev_search_'):
            search_term = command.split('_', 2)[-1]
            logger.info(f"Search for: {search_term}")
            return
        
        # Execute mapped command
        if command in command_map:
            command_map[command]()
            logger.info(f"Executed Vim command: {command}")
        else:
            logger.warning(f"Unknown Vim command: {command}")
            
    except Exception as e:
        logger.error(f"Failed to handle Vim command '{command}': {e}")


def _activate_current_focused(main_window):
    """Activate the currently focused widget."""
    try:
        focused_widget = main_window.focusWidget()
        if focused_widget:
            if hasattr(focused_widget, 'click'):
                focused_widget.click()
            elif hasattr(focused_widget, 'activate'):
                focused_widget.activate()
            elif hasattr(focused_widget, 'setChecked'):
                focused_widget.setChecked(not focused_widget.isChecked())
    except Exception as e:
        logger = get_logger('keyboard_integration')
        logger.error(f"Failed to activate focused widget: {e}")


def _activate_current_item(main_window):
    """Activate the current item in list/tree/table widgets."""
    try:
        focused_widget = main_window.focusWidget()
        if focused_widget and hasattr(focused_widget, 'currentItem'):
            item = focused_widget.currentItem()
            if item:
                focused_widget.itemDoubleClicked.emit(item)
    except Exception as e:
        logger = get_logger('keyboard_integration')
        logger.error(f"Failed to activate current item: {e}")


def _start_search_mode(main_window):
    """Start search mode in the current context."""
    try:
        # Try to focus a search field if available
        if hasattr(main_window, 'search_edit'):
            main_window.search_edit.setFocus()
            main_window.search_edit.selectAll()
        elif hasattr(main_window, 'find_edit'):
            main_window.find_edit.setFocus()
            main_window.find_edit.selectAll()
        else:
            # Create a simple search dialog
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(main_window, 'Search', 'Enter search term:')
            if ok and text:
                logger = get_logger('keyboard_integration')
                logger.info(f"Search term: {text}")
    except Exception as e:
        logger = get_logger('keyboard_integration')
        logger.error(f"Failed to start search mode: {e}")


class KeyboardNavigationDialog(QWidget):
    """Dialog wrapper for keyboard navigation settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Navigation")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.settings = KeyboardNavigationSettings()
        layout.addWidget(self.settings)
        
        self.setStyleSheet("""
            KeyboardNavigationDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
