"""Keyboard-only navigation mode - Vim-style shortcuts with focus rings."""

from PySide6.QtWidgets import (
    QWidget, QApplication, QStyle, QStyleOption, QLabel, QPushButton,
    QListWidget, QTreeWidget, QTableWidget, QAbstractItemView, QComboBox,
    QLineEdit, QTextEdit, QCheckBox, QRadioButton, QSlider, QSpinBox,
    QDoubleSpinBox, QGroupBox, QTabWidget, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QEvent
from PySide6.QtGui import QKeyEvent, QFocusEvent, QPalette, QColor, QPainter, QPen
from src.core.logger import get_logger


class FocusRingStyle:
    """Manages focus ring styling for keyboard navigation."""
    
    def __init__(self):
        self.logger = get_logger('focus_ring_style')
        self.focus_enabled = False
        self.focus_color = QColor(98, 0, 234)  # #6200ea
        self.focus_width = 2
        
    def enable_focus_rings(self, enable=True):
        """Enable or disable focus rings."""
        self.focus_enabled = enable
        self.logger.debug(f"Focus rings {'enabled' if enable else 'disabled'}")
    
    def set_focus_color(self, color):
        """Set focus ring color."""
        self.focus_color = QColor(color)
    
    def apply_focus_style(self, widget):
        """Apply focus ring style to widget."""
        if not self.focus_enabled:
            return
        
        # Create custom stylesheet with focus ring
        widget_name = widget.objectName() or f"widget_{id(widget)}"
        
        style_sheet = f"""
            #{widget_name} {{
                border: 1px solid transparent;
            }}
            #{widget_name}:focus {{
                border: {self.focus_width}px solid {self.focus_color.name()};
                outline: none;
            }}
        """
        
        # Special handling for different widget types
        if isinstance(widget, QPushButton):
            style_sheet += f"""
                #{widget_name}:hover {{
                    border: {self.focus_width}px solid {self.focus_color.name()};
                    background-color: rgba(98, 0, 234, 0.1);
                }}
            """
        elif isinstance(widget, (QListWidget, QTreeWidget, QTableWidget)):
            style_sheet += f"""
                #{widget_name}::item:focus {{
                    border: 1px solid {self.focus_color.name()};
                    background-color: rgba(98, 0, 234, 0.2);
                }}
            """
        elif isinstance(widget, QLineEdit):
            style_sheet += f"""
                #{widget_name}:focus {{
                    border: {self.focus_width}px solid {self.focus_color.name()};
                    background-color: rgba(98, 0, 234, 0.05);
                }}
            """
        
        widget.setStyleSheet(style_sheet)


class KeyboardNavigationManager(QObject):
    """Manages keyboard navigation and Vim-style shortcuts."""
    
    # Signals
    navigation_mode_changed = Signal(bool)  # keyboard navigation enabled/disabled
    vim_command_executed = Signal(str)  # vim command executed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('keyboard_navigation')
        
        self.parent_widget = parent
        self.keyboard_mode_enabled = False
        self.focus_ring_style = FocusRingStyle()
        
        self.current_focus_widget = None
        self.focusable_widgets = []
        self.current_focus_index = 0
        
        # Vim mode state
        self.vim_mode = "normal"  # normal, insert, visual
        self.vim_command_buffer = ""
        self.vim_last_search = ""
        
        # Timer for clearing command buffer
        self.command_timer = QTimer()
        self.command_timer.setSingleShot(True)
        self.command_timer.timeout.connect(self._clear_command_buffer)
        
        self.logger.debug("Keyboard navigation manager initialized")
    
    def enable_keyboard_mode(self, enable=True):
        """Enable or disable keyboard navigation mode."""
        self.keyboard_mode_enabled = enable
        self.focus_ring_style.enable_focus_rings(enable)
        
        if enable:
            self._collect_focusable_widgets()
            self._setup_keyboard_shortcuts()
            self.logger.info("Keyboard navigation mode enabled")
        else:
            self._remove_keyboard_shortcuts()
            self.logger.info("Keyboard navigation mode disabled")
        
        self.navigation_mode_changed.emit(enable)
    
    def _collect_focusable_widgets(self):
        """Collect all focusable widgets in the parent widget."""
        self.focusable_widgets = []
        
        if self.parent_widget:
            self._collect_widgets_recursive(self.parent_widget)
        
        self.logger.debug(f"Found {len(self.focusable_widgets)} focusable widgets")
    
    def _collect_widgets_recursive(self, widget):
        """Recursively collect focusable widgets."""
        # Check if widget is focusable
        if widget.focusPolicy() != Qt.NoFocus and widget.isEnabled():
            self.focusable_widgets.append(widget)
        
        # Check child widgets
        for child in widget.children():
            if isinstance(child, QWidget):
                self._collect_widgets_recursive(child)
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for Vim-style navigation."""
        if self.parent_widget:
            # Install event filter to capture key presses
            self.parent_widget.installEventFilter(self)
    
    def _remove_keyboard_shortcuts(self):
        """Remove keyboard shortcuts."""
        if self.parent_widget:
            self.parent_widget.removeEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Filter events for keyboard shortcuts."""
        if not self.keyboard_mode_enabled or not isinstance(event, QKeyEvent):
            return super().eventFilter(obj, event)
        
        if event.type() == QEvent.KeyPress:
            return self._handle_key_press(event)
        
        return super().eventFilter(obj, event)
    
    def _handle_key_press(self, event):
        """Handle key press events for Vim-style navigation."""
        key = event.key()
        modifiers = event.modifiers()
        
        # Handle Vim-style commands
        if self.vim_mode == "normal":
            return self._handle_vim_normal_mode(key, modifiers)
        elif self.vim_mode == "insert":
            return self._handle_vim_insert_mode(key, modifiers)
        elif self.vim_mode == "visual":
            return self._handle_vim_visual_mode(key, modifiers)
        
        return False
    
    def _handle_vim_normal_mode(self, key, modifiers):
        """Handle Vim normal mode commands."""
        if modifiers == Qt.NoModifier:
            # Navigation commands
            if key == Qt.Key_J:  # Down
                self._navigate_down()
                return True
            elif key == Qt.Key_K:  # Up
                self._navigate_up()
                return True
            elif key == Qt.Key_H:  # Left
                self._navigate_left()
                return True
            elif key == Qt.Key_L:  # Right
                self._navigate_right()
                return True
            elif key == Qt.Key_G:  # Go to bottom
                self._navigate_to_bottom()
                return True
            elif key == Qt.Key_G and modifiers == Qt.ShiftModifier:  # Shift+G - Go to top
                self._navigate_to_top()
                return True
            
            # Action commands
            elif key == Qt.Key_Return or key == Qt.Key_Enter:  # Play/Activate
                self._activate_current_widget()
                return True
            elif key == Qt.Key_Space:  # Play/Pause
                self._toggle_playback()
                return True
            elif key == Qt.Key_O:  # Open file
                self._open_file()
                return True
            elif key == Qt.Key_Q:  # Quit/Close
                self._close_current()
                return True
            elif key == Qt.Key_S:  # Stop
                self._stop_playback()
                return True
            elif key == Qt.Key_F:  # Fullscreen
                self._toggle_fullscreen()
                return True
            elif key == Qt.Key_M:  # Mute
                self._toggle_mute()
                return True
            elif key == Qt.Key_V:  # Volume up
                self._adjust_volume(1)
                return True
            elif key == Qt.Key_V and modifiers == Qt.ShiftModifier:  # Shift+V - Volume down
                self._adjust_volume(-1)
                return True
            
            # Search commands
            elif key == Qt.Key_Slash:  # Search
                self._start_search()
                return True
            elif key == Qt.Key_N:  # Next search result
                self._next_search_result()
                return True
            elif key == Qt.Key_N and modifiers == Qt.ShiftModifier:  # Shift+N - Previous result
                self._previous_search_result()
                return True
            
            # Mode switching
            elif key == Qt.Key_I:  # Insert mode
                self._switch_to_insert_mode()
                return True
            elif key == Qt.Key_Escape:  # Back to normal mode
                self._switch_to_normal_mode()
                return True
        
        return False
    
    def _handle_vim_insert_mode(self, key, modifiers):
        """Handle Vim insert mode commands."""
        if key == Qt.Key_Escape:
            self._switch_to_normal_mode()
            return True
        
        # In insert mode, let the widget handle normal typing
        return False
    
    def _handle_vim_visual_mode(self, key, modifiers):
        """Handle Vim visual mode commands."""
        if key == Qt.Key_Escape:
            self._switch_to_normal_mode()
            return True
        
        # Visual mode navigation (same as normal mode)
        return self._handle_vim_normal_mode(key, modifiers)
    
    def _navigate_down(self):
        """Navigate to next focusable widget."""
        if self.focusable_widgets:
            self.current_focus_index = (self.current_focus_index + 1) % len(self.focusable_widgets)
            self._set_focus_to_widget(self.focusable_widgets[self.current_focus_index])
    
    def _navigate_up(self):
        """Navigate to previous focusable widget."""
        if self.focusable_widgets:
            self.current_focus_index = (self.current_focus_index - 1) % len(self.focusable_widgets)
            self._set_focus_to_widget(self.focusable_widgets[self.current_focus_index])
    
    def _navigate_left(self):
        """Navigate left in current widget (if applicable)."""
        current = self._get_current_focused_widget()
        if current:
            if hasattr(current, 'focusPreviousChild'):
                current.focusPreviousChild(True)
            elif hasattr(current, 'stepDown'):
                current.stepDown()
    
    def _navigate_right(self):
        """Navigate right in current widget (if applicable)."""
        current = self._get_current_focused_widget()
        if current:
            if hasattr(current, 'focusNextChild'):
                current.focusNextChild(True)
            elif hasattr(current, 'stepUp'):
                current.stepUp()
    
    def _navigate_to_bottom(self):
        """Navigate to last focusable widget."""
        if self.focusable_widgets:
            self.current_focus_index = len(self.focusable_widgets) - 1
            self._set_focus_to_widget(self.focusable_widgets[self.current_focus_index])
    
    def _navigate_to_top(self):
        """Navigate to first focusable widget."""
        if self.focusable_widgets:
            self.current_focus_index = 0
            self._set_focus_to_widget(self.focusable_widgets[self.current_focus_index])
    
    def _set_focus_to_widget(self, widget):
        """Set focus to specific widget."""
        if widget and widget.isEnabled():
            widget.setFocus()
            self.current_focus_widget = widget
            
            # Apply focus ring style
            self.focus_ring_style.apply_focus_style(widget)
    
    def _get_current_focused_widget(self):
        """Get currently focused widget."""
        focused_widget = QApplication.focusWidget()
        if focused_widget and focused_widget.isEnabled():
            return focused_widget
        return self.current_focus_widget
    
    def _activate_current_widget(self):
        """Activate/press current focused widget."""
        current = self._get_current_focused_widget()
        if current:
            if isinstance(current, QPushButton):
                current.click()
                self.vim_command_executed.emit("activate")
            elif isinstance(current, (QListWidget, QTreeWidget, QTableWidget)):
                # Activate selected item
                if current.currentItem():
                    current.itemDoubleClicked.emit(current.currentItem())
                    self.vim_command_executed.emit("activate_item")
            elif hasattr(current, 'activated'):
                current.activated.emit()
                self.vim_command_executed.emit("activate")
    
    def _toggle_playback(self):
        """Toggle play/pause."""
        self.vim_command_executed.emit("toggle_playback")
    
    def _stop_playback(self):
        """Stop playback."""
        self.vim_command_executed.emit("stop")
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen."""
        self.vim_command_executed.emit("toggle_fullscreen")
    
    def _toggle_mute(self):
        """Toggle mute."""
        self.vim_command_executed.emit("toggle_mute")
    
    def _adjust_volume(self, direction):
        """Adjust volume up or down."""
        self.vim_command_executed.emit(f"adjust_volume_{direction}")
    
    def _open_file(self):
        """Open file dialog."""
        self.vim_command_executed.emit("open_file")
    
    def _close_current(self):
        """Close current widget/dialog."""
        self.vim_command_executed.emit("close")
    
    def _start_search(self):
        """Start search mode."""
        self.vim_mode = "search"
        self.vim_command_executed.emit("start_search")
    
    def _next_search_result(self):
        """Go to next search result."""
        if self.vim_last_search:
            self.vim_command_executed.emit(f"next_search_{self.vim_last_search}")
    
    def _previous_search_result(self):
        """Go to previous search result."""
        if self.vim_last_search:
            self.vim_command_executed.emit(f"prev_search_{self.vim_last_search}")
    
    def _switch_to_insert_mode(self):
        """Switch to insert mode."""
        self.vim_mode = "insert"
        self.vim_command_executed.emit("insert_mode")
    
    def _switch_to_normal_mode(self):
        """Switch to normal mode."""
        self.vim_mode = "normal"
        self.vim_command_executed.emit("normal_mode")
    
    def _switch_to_visual_mode(self):
        """Switch to visual mode."""
        self.vim_mode = "visual"
        self.vim_command_executed.emit("visual_mode")
    
    def _clear_command_buffer(self):
        """Clear command buffer."""
        self.vim_command_buffer = ""
    
    def get_current_mode(self):
        """Get current Vim mode."""
        return self.vim_mode
    
    def is_keyboard_mode_enabled(self):
        """Check if keyboard navigation mode is enabled."""
        return self.keyboard_mode_enabled


class KeyboardNavigationSettings(QWidget):
    """Settings widget for keyboard navigation configuration."""
    
    settings_changed = Signal(dict)  # settings dictionary
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('keyboard_nav_settings')
        
        self._setup_ui()
        
        self.logger.debug("Keyboard navigation settings initialized")
    
    def _setup_ui(self):
        """Setup the settings UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header_label = QLabel("Keyboard Navigation Settings")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                padding: 8px;
            }
        """)
        layout.addWidget(header_label)
        
        # Enable keyboard mode
        self.enable_cb = QCheckBox("Enable Keyboard-Only Navigation Mode")
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
        layout.addWidget(self.enable_cb)
        
        # Focus ring settings
        focus_group = QGroupBox("Focus Ring Settings")
        focus_group.setStyleSheet("""
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
        
        focus_layout = QVBoxLayout()
        
        # Focus ring color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Focus Ring Color:"))
        
        self.color_combo = QComboBox()
        self.color_combo.addItems([
            ("#6200ea", "Default Purple"),
            ("#4caf50", "Green"),
            ("#2196f3", "Blue"),
            ("#ff9800", "Orange"),
            ("#f44336", "Red"),
            ("#9c27b0", "Purple"),
            ("#607d8b", "Blue Grey")
        ])
        self.color_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #ffffff;
                margin-right: 4px;
            }
        """)
        self.color_combo.currentTextChanged.connect(self._on_settings_changed)
        color_layout.addWidget(self.color_combo)
        color_layout.addStretch()
        
        focus_layout.addLayout(color_layout)
        
        # Focus ring width
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Focus Ring Width:"))
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 5)
        self.width_spin.setValue(2)
        self.width_spin.setStyleSheet("""
            QSpinBox {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px;
            }
            QSpinBox:focus {
                border-color: #6200ea;
            }
        """)
        self.width_spin.valueChanged.connect(self._on_settings_changed)
        width_layout.addWidget(self.width_spin)
        width_layout.addStretch()
        
        focus_layout.addLayout(width_layout)
        focus_group.setLayout(focus_layout)
        layout.addWidget(focus_group)
        
        # Vim shortcuts reference
        shortcuts_group = QGroupBox("Vim-Style Shortcuts")
        shortcuts_group.setStyleSheet("""
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
        
        shortcuts_layout = QVBoxLayout()
        
        shortcuts_text = QLabel("""
<b>Navigation:</b>
• J/K - Move up/down
• H/L - Move left/right
• G/Shift+G - Go to bottom/top
• Enter - Play/Activate

<b>Playback:</b>
• Space - Play/Pause
• S - Stop
• F - Fullscreen
• M - Mute
• V/Shift+V - Volume up/down

<b>File:</b>
• O - Open file
• Q - Close/Quit

<b>Search:</b>
• / - Start search
• N/Shift+N - Next/Previous result

<b>Modes:</b>
• I - Insert mode
• Escape - Normal mode
        """)
        shortcuts_text.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 10px;
                font-family: 'Consolas', monospace;
                line-height: 1.4;
                padding: 8px;
            }
        """)
        shortcuts_text.setWordWrap(False)
        
        shortcuts_layout.addWidget(shortcuts_text)
        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)
        
        layout.addStretch()
        
        # Set dark theme
        self.setStyleSheet("""
            KeyboardNavigationSettings {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
    
    def _on_settings_changed(self):
        """Handle settings changes."""
        settings = {
            'enabled': self.enable_cb.isChecked(),
            'focus_color': self.color_combo.currentData() or self.color_combo.currentText().split()[0],
            'focus_width': self.width_spin.value()
        }
        
        self.settings_changed.emit(settings)
    
    def get_settings(self):
        """Get current settings."""
        return {
            'enabled': self.enable_cb.isChecked(),
            'focus_color': self.color_combo.currentData() or self.color_combo.currentText().split()[0],
            'focus_width': self.width_spin.value()
        }
    
    def set_settings(self, settings):
        """Set settings from dictionary."""
        self.enable_cb.setChecked(settings.get('enabled', False))
        
        color = settings.get('focus_color', '#6200ea')
        for i in range(self.color_combo.count()):
            if self.color_combo.itemData(i) == color:
                self.color_combo.setCurrentIndex(i)
                break
        
        self.width_spin.setValue(settings.get('focus_width', 2))
