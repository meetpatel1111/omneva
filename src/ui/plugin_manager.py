"""Plugin Manager UI - Interface for managing Omneva plugins."""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QGroupBox, QMessageBox, QFileDialog, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QProgressBar, QCheckBox, QFrame, QSplitter, QToolButton,
    QMenu, QAction, QListWidget, QListWidgetItem, QDialog,
    QDialogButtonBox, QTabWidget, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QPixmap, QFont
from src.core.logger import get_logger
from src.core.plugin_system import PluginManager, BasePlugin, create_example_plugin


class PluginInfoWidget(QWidget):
    """Widget for displaying plugin information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('plugin_info_widget')
        
        self._setup_ui()
        
        self.logger.debug("Plugin info widget initialized")
    
    def _setup_ui(self):
        """Setup the plugin info UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Plugin name
        self.name_label = QLabel("No plugin selected")
        self.name_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                padding: 4px;
            }
        """)
        layout.addWidget(self.name_label)
        
        # Plugin details
        details_layout = QFormLayout()
        
        self.version_label = QLabel("")
        self.author_label = QLabel("")
        self.website_label = QLabel("")
        self.status_label = QLabel("")
        
        details_layout.addRow("Version:", self.version_label)
        details_layout.addRow("Author:", self.author_label)
        details_layout.addRow("Website:", self.website_label)
        details_layout.addRow("Status:", self.status_label)
        
        layout.addLayout(details_layout)
        
        # Description
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        layout.addWidget(desc_label)
        
        self.description_text = QTextEdit()
        self.description_text.setMaximumHeight(80)
        self.description_text.setReadOnly(True)
        self.description_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.description_text)
        
        # Capabilities
        caps_label = QLabel("Capabilities:")
        caps_label.setStyleSheet("color: #cccccc; font-size: 11px;")
        layout.addWidget(caps_label)
        
        self.capabilities_text = QTextEdit()
        self.capabilities_text.setMaximumHeight(60)
        self.capabilities_text.setReadOnly(True)
        self.capabilities_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.capabilities_text)
        
        layout.addStretch()
        
        # Set dark theme
        self.setStyleSheet("""
            PluginInfoWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
    
    def set_plugin_info(self, plugin_info):
        """Set plugin information display."""
        if plugin_info:
            self.name_label.setText(plugin_info.get('name', 'Unknown'))
            self.version_label.setText(plugin_info.get('version', ''))
            self.author_label.setText(plugin_info.get('author', ''))
            self.website_label.setText(plugin_info.get('website', ''))
            
            status = "Enabled" if plugin_info.get('enabled', False) else "Disabled"
            if plugin_info.get('initialized', False):
                status += " (Initialized)"
            else:
                status += " (Not Initialized)"
            self.status_label.setText(status)
            
            self.description_text.setPlainText(plugin_info.get('description', ''))
            
            capabilities = plugin_info.get('capabilities', [])
            self.capabilities_text.setPlainText(', '.join(capabilities) if capabilities else 'None')
        else:
            self.clear_info()
    
    def clear_info(self):
        """Clear plugin information."""
        self.name_label.setText("No plugin selected")
        self.version_label.setText("")
        self.author_label.setText("")
        self.website_label.setText("")
        self.status_label.setText("")
        self.description_text.clear()
        self.capabilities_text.clear()


class PluginManagerWidget(QWidget):
    """Main plugin manager widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('plugin_manager_widget')
        
        self.plugin_manager = PluginManager()
        self.selected_plugin = None
        
        self._setup_ui()
        self._setup_connections()
        
        self.logger.debug("Plugin manager widget initialized")
    
    def _setup_ui(self):
        """Setup the plugin manager UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Header
        header_label = QLabel("Plugin Manager")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
                padding: 8px;
            }
        """)
        layout.addWidget(header_label)
        
        # Main content
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Plugin list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Plugin list controls
        controls_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #6200ea;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #7c4dff;
            }
        """)
        self.refresh_btn.clicked.connect(self._refresh_plugins)
        controls_layout.addWidget(self.refresh_btn)
        
        self.load_all_btn = QPushButton("📦 Load All")
        self.load_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #66bb6a;
            }
        """)
        self.load_all_btn.clicked.connect(self._load_all_plugins)
        controls_layout.addWidget(self.load_all_btn)
        
        self.unload_all_btn = QPushButton("📦 Unload All")
        self.unload_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #ef5350;
            }
        """)
        self.unload_all_btn.clicked.connect(self._unload_all_plugins)
        controls_layout.addWidget(self.unload_all_btn)
        
        controls_layout.addStretch()
        left_layout.addLayout(controls_layout)
        
        # Plugin list
        self.plugin_list = QListWidget()
        self.plugin_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                selection-background-color: #6200ea;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:selected {
                background-color: #6200ea;
                color: #ffffff;
            }
        """)
        self.plugin_list.itemSelectionChanged.connect(self._on_plugin_selection_changed)
        self.plugin_list.itemDoubleClicked.connect(self._toggle_plugin)
        left_layout.addWidget(self.plugin_list)
        
        content_splitter.addWidget(left_panel)
        
        # Right panel - Plugin info and actions
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Plugin info
        self.plugin_info = PluginInfoWidget()
        right_layout.addWidget(self.plugin_info)
        
        # Plugin actions
        actions_group = QGroupBox("Plugin Actions")
        actions_group.setStyleSheet("""
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
        
        actions_layout = QVBoxLayout()
        
        # Action buttons
        self.load_btn = QPushButton("Load Plugin")
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #66bb6a;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.load_btn.clicked.connect(self._load_selected_plugin)
        actions_layout.addWidget(self.load_btn)
        
        self.unload_btn = QPushButton("Unload Plugin")
        self.unload_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #ffa726;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.unload_btn.clicked.connect(self._unload_selected_plugin)
        actions_layout.addWidget(self.unload_btn)
        
        self.reload_btn = QPushButton("Reload Plugin")
        self.reload_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #42a5f5;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.reload_btn.clicked.connect(self._reload_selected_plugin)
        actions_layout.addWidget(self.reload_btn)
        
        # Enable/Disable checkbox
        self.enable_cb = QCheckBox("Enable Plugin")
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
        self.enable_cb.toggled.connect(self._toggle_plugin_enabled)
        actions_layout.addWidget(self.enable_cb)
        
        actions_layout.addStretch()
        actions_group.setLayout(actions_layout)
        right_layout.addWidget(actions_group)
        
        # Plugin directory info
        info_group = QGroupBox("Plugin Directories")
        info_group.setStyleSheet("""
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
        
        info_layout = QVBoxLayout()
        
        self.dirs_text = QTextEdit()
        self.dirs_text.setMaximumHeight(80)
        self.dirs_text.setReadOnly(True)
        self.dirs_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px;
                font-size: 9px;
                font-family: 'Consolas', monospace;
            }
        """)
        
        # Display plugin directories
        dirs_info = []
        for directory in self.plugin_manager.plugin_directories:
            dirs_info.append(f"• {directory}")
        
        self.dirs_text.setPlainText('\n'.join(dirs_info))
        info_layout.addWidget(self.dirs_text)
        
        # Create example plugin button
        create_example_btn = QPushButton("Create Example Plugin")
        create_example_btn.setStyleSheet("""
            QPushButton {
                background-color: #9c27b0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #ab47bc;
            }
        """)
        create_example_btn.clicked.connect(self._create_example_plugin)
        info_layout.addWidget(create_example_btn)
        
        info_group.setLayout(info_layout)
        right_layout.addWidget(info_group)
        
        content_splitter.addWidget(right_panel)
        
        # Set splitter sizes
        content_splitter.setSizes([300, 400])
        layout.addWidget(content_splitter)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 9px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Set dark theme
        self.setStyleSheet("""
            PluginManagerWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
    
    def _setup_connections(self):
        """Setup signal connections."""
        self.plugin_manager.plugin_loaded.connect(self._on_plugin_loaded)
        self.plugin_manager.plugin_unloaded.connect(self._on_plugin_unloaded)
        self.plugin_manager.plugin_error.connect(self._on_plugin_error)
        self.plugin_manager.all_plugins_loaded.connect(self._on_all_plugins_loaded)
    
    def _refresh_plugins(self):
        """Refresh plugin discovery."""
        self.status_label.setText("Discovering plugins...")
        self.plugin_list.clear()
        self.plugin_info.clear_info()
        
        self.plugin_manager.discover_plugins()
        self._update_plugin_list()
        
        self.status_label.setText(f"Found {len(self.plugin_manager.plugin_classes)} plugins")
    
    def _update_plugin_list(self):
        """Update the plugin list display."""
        self.plugin_list.clear()
        
        for plugin_name in self.plugin_manager.plugin_classes:
            item = QListWidgetItem(plugin_name)
            
            # Check if plugin is loaded
            if plugin_name in self.plugin_manager.plugins:
                plugin = self.plugin_manager.plugins[plugin_name]
                if plugin.enabled:
                    item.setText(f"✅ {plugin_name}")
                else:
                    item.setText(f"⏸ {plugin_name}")
            else:
                item.setText(f"○ {plugin_name}")
            
            self.plugin_list.addItem(item)
    
    def _load_all_plugins(self):
        """Load all discovered plugins."""
        self.status_label.setText("Loading all plugins...")
        self.plugin_manager.load_all_plugins()
    
    def _unload_all_plugins(self):
        """Unload all plugins."""
        self.status_label.setText("Unloading all plugins...")
        self.plugin_manager.unload_all_plugins()
        self._update_plugin_list()
        self.plugin_info.clear_info()
        self.status_label.setText("All plugins unloaded")
    
    def _load_selected_plugin(self):
        """Load the selected plugin."""
        if self.selected_plugin:
            self.status_label.setText(f"Loading plugin {self.selected_plugin}...")
            self.plugin_manager.load_plugin(self.selected_plugin)
    
    def _unload_selected_plugin(self):
        """Unload the selected plugin."""
        if self.selected_plugin:
            self.status_label.setText(f"Unloading plugin {self.selected_plugin}...")
            self.plugin_manager.unload_plugin(self.selected_plugin)
    
    def _reload_selected_plugin(self):
        """Reload the selected plugin."""
        if self.selected_plugin:
            self.status_label.setText(f"Reloading plugin {self.selected_plugin}...")
            self.plugin_manager.reload_plugin(self.selected_plugin)
    
    def _toggle_plugin_enabled(self, enabled):
        """Toggle plugin enabled state."""
        if self.selected_plugin:
            if enabled:
                self.plugin_manager.enable_plugin(self.selected_plugin)
            else:
                self.plugin_manager.disable_plugin(self.selected_plugin)
            
            self._update_plugin_list()
            self._update_plugin_info()
    
    def _toggle_plugin(self):
        """Toggle plugin load/unload state."""
        if self.selected_plugin:
            if self.selected_plugin in self.plugin_manager.plugins:
                self._unload_selected_plugin()
            else:
                self._load_selected_plugin()
    
    def _create_example_plugin(self):
        """Create an example plugin file."""
        if create_example_plugin():
            QMessageBox.information(self, "Success", 
                                      "Example plugin created successfully!\n"
                                      "You can find it in the plugins directory.")
            self._refresh_plugins()
        else:
            QMessageBox.critical(self, "Error", 
                                "Failed to create example plugin.")
    
    def _on_plugin_selection_changed(self):
        """Handle plugin selection change."""
        current_item = self.plugin_list.currentItem()
        if current_item:
            # Extract plugin name from display text
            display_text = current_item.text()
            self.selected_plugin = display_text.lstrip("✅⏸○ ").strip()
            
            self._update_plugin_info()
            self._update_action_buttons()
        else:
            self.selected_plugin = None
            self.plugin_info.clear_info()
            self._update_action_buttons()
    
    def _update_plugin_info(self):
        """Update plugin information display."""
        if self.selected_plugin:
            plugin_info = self.plugin_manager.get_plugin_info(self.selected_plugin)
            self.plugin_info.set_plugin_info(plugin_info)
        else:
            self.plugin_info.clear_info()
    
    def _update_action_buttons(self):
        """Update action button states."""
        has_selection = self.selected_plugin is not None
        is_loaded = self.selected_plugin in self.plugin_manager.plugins if has_selection else False
        
        self.load_btn.setEnabled(has_selection and not is_loaded)
        self.unload_btn.setEnabled(has_selection and is_loaded)
        self.reload_btn.setEnabled(has_selection and is_loaded)
        self.enable_cb.setEnabled(has_selection and is_loaded)
        
        if has_selection and is_loaded:
            plugin = self.plugin_manager.plugins[self.selected_plugin]
            self.enable_cb.setChecked(plugin.enabled)
        else:
            self.enable_cb.setChecked(False)
    
    def _on_plugin_loaded(self, plugin_name):
        """Handle plugin loaded event."""
        self.status_label.setText(f"Plugin {plugin_name} loaded successfully")
        self._update_plugin_list()
        
        if self.selected_plugin == plugin_name:
            self._update_plugin_info()
            self._update_action_buttons()
    
    def _on_plugin_unloaded(self, plugin_name):
        """Handle plugin unloaded event."""
        self.status_label.setText(f"Plugin {plugin_name} unloaded")
        self._update_plugin_list()
        
        if self.selected_plugin == plugin_name:
            self.plugin_info.clear_info()
            self._update_action_buttons()
    
    def _on_plugin_error(self, plugin_name, error_message):
        """Handle plugin error event."""
        self.status_label.setText(f"Error in plugin {plugin_name}: {error_message}")
        QMessageBox.critical(self, "Plugin Error", 
                            f"Error in plugin {plugin_name}:\n{error_message}")
    
    def _on_all_plugins_loaded(self):
        """Handle all plugins loaded event."""
        self._update_plugin_list()
        self.status_label.setText("All plugins loaded")


class PluginManagerDialog(QWidget):
    """Dialog wrapper for plugin manager."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plugin Manager")
        self.setFixedSize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.manager = PluginManagerWidget()
        layout.addWidget(self.manager)
        
        self.setStyleSheet("""
            PluginManagerDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
