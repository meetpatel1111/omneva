"""Plugin System - BasePlugin class and plugin loading architecture."""

import os
import sys
import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from PySide6.QtCore import QObject, Signal
from src.core.logger import get_logger
from src.core.storage import storage


class BasePlugin(ABC):
    """Base class for all Omneva plugins."""
    
    # Plugin metadata
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    website: str = ""
    
    # Plugin capabilities
    capabilities: List[str] = []
    
    def __init__(self):
        self.logger = get_logger(f'plugin.{self.name}')
        self.enabled = False
        self.initialized = False
        
    @abstractmethod
    def initialize(self, main_window) -> bool:
        """Initialize the plugin. Return True if successful."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get plugin information."""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'website': self.website,
            'capabilities': self.capabilities,
            'enabled': self.enabled,
            'initialized': self.initialized
        }
    
    def on_media_loaded(self, file_path: str) -> None:
        """Called when media is loaded."""
        pass
    
    def on_playback_started(self) -> None:
        """Called when playback starts."""
        pass
    
    def on_playback_stopped(self) -> None:
        """Called when playback stops."""
        pass
    
    def on_playback_paused(self) -> None:
        """Called when playback is paused."""
        pass
    
    def on_playback_resumed(self) -> None:
        """Called when playback is resumed."""
        pass
    
    def add_menu_item(self, menu_path: str, action_name: str, callback) -> None:
        """Add a menu item to the application."""
        # This will be implemented by the plugin manager
        if hasattr(self, '_plugin_manager'):
            self._plugin_manager.add_menu_item(menu_path, action_name, callback)
    
    def add_toolbar_item(self, widget_name: str, widget) -> None:
        """Add a toolbar item to the application."""
        if hasattr(self, '_plugin_manager'):
            self._plugin_manager.add_toolbar_item(widget_name, widget)
    
    def add_settings_page(self, page_name: str, widget_class) -> None:
        """Add a settings page to the application."""
        if hasattr(self, '_plugin_manager'):
            self._plugin_manager.add_settings_page(page_name, widget_class)


class PluginManager(QObject):
    """Manages loading, unloading, and coordination of plugins."""
    
    # Signals
    plugin_loaded = Signal(str)  # plugin name
    plugin_unloaded = Signal(str)  # plugin name
    plugin_error = Signal(str, str)  # plugin name, error message
    all_plugins_loaded = Signal()  # all plugins loaded
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('plugin_manager')
        
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_classes: Dict[str, Type[BasePlugin]] = {}
        
        self.plugin_directories = [
            os.path.join(storage.get_app_data_dir(), 'plugins'),
            os.path.join(os.path.dirname(__file__), '..', 'plugins'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'plugins')  # For development
        ]
        
        self.main_window = None
        self.menu_extensions = {}
        self.toolbar_extensions = {}
        self.settings_extensions = {}
        
        self._ensure_plugin_directories()
        
        self.logger.debug("Plugin manager initialized")
    
    def _ensure_plugin_directories(self):
        """Ensure plugin directories exist."""
        for directory in self.plugin_directories:
            try:
                os.makedirs(directory, exist_ok=True)
                self.logger.debug(f"Plugin directory ensured: {directory}")
            except Exception as e:
                self.logger.error(f"Failed to create plugin directory {directory}: {e}")
    
    def set_main_window(self, main_window):
        """Set the main window reference for plugins."""
        self.main_window = main_window
    
    def discover_plugins(self):
        """Discover all available plugins."""
        self.logger.info("Discovering plugins...")
        
        discovered_count = 0
        for directory in self.plugin_directories:
            if not os.path.exists(directory):
                continue
            
            for filename in os.listdir(directory):
                if filename.endswith('.py') and not filename.startswith('_'):
                    plugin_path = os.path.join(directory, filename)
                    plugin_name = filename[:-3]  # Remove .py extension
                    
                    try:
                        self._load_plugin_class(plugin_path, plugin_name)
                        discovered_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to load plugin class from {plugin_path}: {e}")
        
        self.logger.info(f"Discovered {discovered_count} plugin classes")
    
    def _load_plugin_class(self, plugin_path: str, plugin_name: str):
        """Load a plugin class from file."""
        # Add plugin directory to Python path
        plugin_dir = os.path.dirname(plugin_path)
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
        
        try:
            # Import the module
            module_name = os.path.splitext(os.path.basename(plugin_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find BasePlugin subclasses
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BasePlugin) and 
                    obj is not BasePlugin and 
                    obj.__module__ == module.__name__):
                    
                    self.plugin_classes[plugin_name] = obj
                    self.logger.debug(f"Loaded plugin class: {plugin_name}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Failed to load plugin class from {plugin_path}: {e}")
            raise
        finally:
            # Remove plugin directory from Python path
            if plugin_dir in sys.path:
                sys.path.remove(plugin_dir)
    
    def load_plugin(self, plugin_name: str) -> bool:
        """Load and initialize a plugin."""
        if plugin_name in self.plugins:
            self.logger.warning(f"Plugin {plugin_name} is already loaded")
            return True
        
        if plugin_name not in self.plugin_classes:
            self.logger.error(f"Plugin class {plugin_name} not found")
            return False
        
        try:
            # Create plugin instance
            plugin_class = self.plugin_classes[plugin_name]
            plugin = plugin_class()
            
            # Set plugin manager reference
            plugin._plugin_manager = self
            
            # Initialize plugin
            if plugin.initialize(self.main_window):
                plugin.enabled = True
                plugin.initialized = True
                self.plugins[plugin_name] = plugin
                
                self.logger.info(f"Plugin {plugin_name} loaded successfully")
                self.plugin_loaded.emit(plugin_name)
                return True
            else:
                self.logger.error(f"Plugin {plugin_name} failed to initialize")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_name}: {e}")
            self.plugin_error.emit(plugin_name, str(e))
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin."""
        if plugin_name not in self.plugins:
            self.logger.warning(f"Plugin {plugin_name} is not loaded")
            return True
        
        try:
            plugin = self.plugins[plugin_name]
            
            # Cleanup plugin
            plugin.cleanup()
            plugin.enabled = False
            plugin.initialized = False
            
            # Remove from plugins dict
            del self.plugins[plugin_name]
            
            self.logger.info(f"Plugin {plugin_name} unloaded successfully")
            self.plugin_unloaded.emit(plugin_name)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False
    
    def load_all_plugins(self):
        """Load all discovered plugins."""
        self.logger.info("Loading all plugins...")
        
        loaded_count = 0
        failed_count = 0
        
        for plugin_name in self.plugin_classes:
            if self.load_plugin(plugin_name):
                loaded_count += 1
            else:
                failed_count += 1
        
        self.logger.info(f"Loaded {loaded_count} plugins, {failed_count} failed")
        self.all_plugins_loaded.emit()
    
    def unload_all_plugins(self):
        """Unload all loaded plugins."""
        self.logger.info("Unloading all plugins...")
        
        plugin_names = list(self.plugins.keys())
        for plugin_name in plugin_names:
            self.unload_plugin(plugin_name)
        
        self.logger.info("All plugins unloaded")
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get a loaded plugin by name."""
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """Get all loaded plugins."""
        return self.plugins.copy()
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get plugin information."""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            return plugin.get_info()
        return None
    
    def get_all_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information for all plugins."""
        return [plugin.get_info() for plugin in self.plugins.values()]
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin."""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.enabled = True
            self.logger.info(f"Plugin {plugin_name} enabled")
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin."""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            plugin.enabled = False
            self.logger.info(f"Plugin {plugin_name} disabled")
            return True
        return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin."""
        if plugin_name in self.plugins:
            self.unload_plugin(plugin_name)
        
        return self.load_plugin(plugin_name)
    
    def call_plugin_method(self, plugin_name: str, method_name: str, *args, **kwargs) -> Any:
        """Call a method on a specific plugin."""
        plugin = self.get_plugin(plugin_name)
        if plugin and plugin.enabled:
            if hasattr(plugin, method_name):
                method = getattr(plugin, method_name)
                return method(*args, **kwargs)
            else:
                self.logger.warning(f"Plugin {plugin_name} does not have method {method_name}")
        else:
            self.logger.warning(f"Plugin {plugin_name} is not loaded or enabled")
        
        return None
    
    def call_all_plugins_method(self, method_name: str, *args, **kwargs) -> Dict[str, Any]:
        """Call a method on all enabled plugins."""
        results = {}
        
        for plugin_name, plugin in self.plugins.items():
            if plugin.enabled and hasattr(plugin, method_name):
                try:
                    method = getattr(plugin, method_name)
                    results[plugin_name] = method(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Error calling {method_name} on plugin {plugin_name}: {e}")
                    results[plugin_name] = None
        
        return results
    
    # Menu extension methods
    def add_menu_item(self, menu_path: str, action_name: str, callback):
        """Add a menu item for plugins."""
        if menu_path not in self.menu_extensions:
            self.menu_extensions[menu_path] = {}
        
        self.menu_extensions[menu_path][action_name] = callback
        self.logger.debug(f"Added menu item: {menu_path} -> {action_name}")
    
    def add_toolbar_item(self, widget_name: str, widget):
        """Add a toolbar item for plugins."""
        self.toolbar_extensions[widget_name] = widget
        self.logger.debug(f"Added toolbar item: {widget_name}")
    
    def add_settings_page(self, page_name: str, widget_class):
        """Add a settings page for plugins."""
        self.settings_extensions[page_name] = widget_class
        self.logger.debug(f"Added settings page: {page_name}")
    
    def get_menu_extensions(self) -> Dict[str, Dict[str, Any]]:
        """Get all menu extensions."""
        return self.menu_extensions.copy()
    
    def get_toolbar_extensions(self) -> Dict[str, Any]:
        """Get all toolbar extensions."""
        return self.toolbar_extensions.copy()
    
    def get_settings_extensions(self) -> Dict[str, Type]:
        """Get all settings extensions."""
        return self.settings_extensions.copy()
    
    def cleanup(self):
        """Cleanup all plugins and resources."""
        self.unload_all_plugins()
        self.plugins.clear()
        self.plugin_classes.clear()
        self.menu_extensions.clear()
        self.toolbar_extensions.clear()
        self.settings_extensions.clear()


# Example plugin for demonstration
class ExamplePlugin(BasePlugin):
    """Example plugin that demonstrates the plugin system."""
    
    name = "Example Plugin"
    version = "1.0.0"
    description = "A simple example plugin for demonstration"
    author = "Omneva Team"
    website = "https://github.com/omneva/omneva"
    capabilities = ["example", "demo"]
    
    def initialize(self, main_window) -> bool:
        """Initialize the example plugin."""
        self.logger.info("Initializing example plugin")
        
        # Add a menu item
        self.add_menu_item("Tools", "Example Action", self._example_action)
        
        # Add a toolbar item
        from PySide6.QtWidgets import QPushButton
        button = QPushButton("Example")
        button.clicked.connect(self._example_action)
        self.add_toolbar_item("example_button", button)
        
        return True
    
    def cleanup(self) -> None:
        """Cleanup the example plugin."""
        self.logger.info("Cleaning up example plugin")
    
    def _example_action(self):
        """Example action callback."""
        self.logger.info("Example action triggered")
        
        # Show a message
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(None, "Example Plugin", "This is an example plugin action!")
    
    def on_media_loaded(self, file_path: str) -> None:
        """Called when media is loaded."""
        self.logger.info(f"Example plugin: Media loaded: {file_path}")
    
    def on_playback_started(self) -> None:
        """Called when playback starts."""
        self.logger.info("Example plugin: Playback started")


# Plugin loader utility functions
def create_example_plugin():
    """Create an example plugin file for users."""
    plugins_dir = os.path.join(storage.get_app_data_dir(), 'plugins')
    os.makedirs(plugins_dir, exist_ok=True)
    
    example_plugin_path = os.path.join(plugins_dir, 'example_plugin.py')
    
    if not os.path.exists(example_plugin_path):
        example_code = '''"""Example Plugin - A template for creating Omneva plugins."""

from src.core.plugin_system import BasePlugin
from PySide6.QtWidgets import QMessageBox

class ExamplePlugin(BasePlugin):
    """Example plugin that demonstrates the plugin system."""
    
    name = "Example Plugin"
    version = "1.0.0"
    description = "A simple example plugin for demonstration"
    author = "Your Name"
    website = "https://your-website.com"
    capabilities = ["example", "demo"]
    
    def initialize(self, main_window) -> bool:
        """Initialize the plugin."""
        self.logger.info("Initializing example plugin")
        
        # Add menu items, toolbar items, etc.
        self.add_menu_item("Tools", "Example Action", self._example_action)
        
        return True
    
    def cleanup(self) -> None:
        """Cleanup the plugin."""
        self.logger.info("Cleaning up example plugin")
    
    def _example_action(self):
        """Example action callback."""
        self.logger.info("Example action triggered")
        QMessageBox.information(None, "Example Plugin", "This is an example plugin action!")
    
    def on_media_loaded(self, file_path: str) -> None:
        """Called when media is loaded."""
        self.logger.info(f"Media loaded: {file_path}")
    
    def on_playback_started(self) -> None:
        """Called when playback starts."""
        self.logger.info("Playback started")
'''
        
        try:
            with open(example_plugin_path, 'w') as f:
                f.write(example_code)
            
            logger = get_logger('plugin_system')
            logger.info(f"Created example plugin: {example_plugin_path}")
            return True
            
        except Exception as e:
            logger = get_logger('plugin_system')
            logger.error(f"Failed to create example plugin: {e}")
            return False
    
    return False
