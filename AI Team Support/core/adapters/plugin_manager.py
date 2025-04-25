"""
Plugin manager for Task Manager.
Handles loading, registering, and managing plugins.
"""
import os
import importlib
import inspect
from typing import Dict, List, Type, Optional

from core.adapters.plugin_base import PluginBase

class PluginManager:
    """Manages plugins for the Task Manager."""
    
    def __init__(self):
        """Initialize the plugin manager."""
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_classes: Dict[str, Type[PluginBase]] = {}
    
    def discover_plugins(self, plugin_dirs: List[str]) -> None:
        """
        Discover available plugins in the specified directories.
        
        Args:
            plugin_dirs: List of directories to search for plugins.
        """
        for plugin_dir in plugin_dirs:
            self._discover_in_directory(plugin_dir)
    
    def _discover_in_directory(self, plugin_dir: str) -> None:
        """
        Discover plugins in a specific directory.
        
        Args:
            plugin_dir: Directory to search for plugins.
        """
        if not os.path.exists(plugin_dir):
            print(f"Plugin directory does not exist: {plugin_dir}")
            return
        
        # Get all Python files in the directory
        for root, _, files in os.walk(plugin_dir):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    # Convert file path to module path
                    file_path = os.path.join(root, file)
                    module_path = file_path.replace('/', '.').replace('\\', '.').replace('.py', '')
                    
                    # If the module path starts with a dot, remove it
                    if module_path.startswith('.'):
                        module_path = module_path[1:]
                    
                    try:
                        # Import the module
                        module = importlib.import_module(module_path)
                        
                        # Find all plugin classes in the module
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, PluginBase) and 
                                obj != PluginBase):
                                self.plugin_classes[obj.__name__] = obj
                                print(f"Discovered plugin: {obj.__name__}")
                    except Exception as e:
                        print(f"Error loading plugin module {module_path}: {e}")
    
    def register_plugin(self, plugin_class: Type[PluginBase], config: Optional[dict] = None) -> bool:
        """
        Register a plugin.
        
        Args:
            plugin_class: The plugin class to register.
            config: Configuration to pass to the plugin.
            
        Returns:
            bool: True if registration was successful, False otherwise.
        """
        try:
            # Create an instance of the plugin
            plugin = plugin_class(config)
            plugin_id = plugin.id
            
            # Check if a plugin with this ID is already registered
            if plugin_id in self.plugins:
                print(f"Plugin with ID {plugin_id} is already registered")
                return False
            
            # Initialize the plugin
            if not plugin.initialize():
                print(f"Failed to initialize plugin: {plugin_id}")
                return False
            
            # Register the plugin
            self.plugins[plugin_id] = plugin
            print(f"Registered plugin: {plugin}")
            return True
        except Exception as e:
            print(f"Error registering plugin {plugin_class.__name__}: {e}")
            return False
    
    def register_plugin_by_name(self, plugin_name: str, config: Optional[dict] = None) -> bool:
        """
        Register a plugin by its class name.
        
        Args:
            plugin_name: Name of the plugin class to register.
            config: Configuration to pass to the plugin.
            
        Returns:
            bool: True if registration was successful, False otherwise.
        """
        if plugin_name not in self.plugin_classes:
            print(f"No plugin named {plugin_name} has been discovered")
            return False
        
        return self.register_plugin(self.plugin_classes[plugin_name], config)
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        Unregister a plugin.
        
        Args:
            plugin_id: ID of the plugin to unregister.
            
        Returns:
            bool: True if unregistration was successful, False otherwise.
        """
        if plugin_id not in self.plugins:
            print(f"No plugin with ID {plugin_id} is registered")
            return False
        
        # Shutdown the plugin
        plugin = self.plugins[plugin_id]
        if not plugin.shutdown():
            print(f"Failed to properly shutdown plugin: {plugin_id}")
        
        # Remove the plugin
        del self.plugins[plugin_id]
        print(f"Unregistered plugin: {plugin_id}")
        return True
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """
        Get a plugin by its ID.
        
        Args:
            plugin_id: ID of the plugin to get.
            
        Returns:
            Optional[PluginBase]: The plugin, or None if not found.
        """
        return self.plugins.get(plugin_id)
    
    def get_plugins_by_type(self, plugin_type: Type[PluginBase]) -> List[PluginBase]:
        """
        Get all plugins of a specific type.
        
        Args:
            plugin_type: Type of plugins to get.
            
        Returns:
            List[PluginBase]: List of plugins matching the type.
        """
        return [plugin for plugin in self.plugins.values() 
                if isinstance(plugin, plugin_type)]
    
    def get_all_plugins(self) -> List[PluginBase]:
        """
        Get all registered plugins.
        
        Returns:
            List[PluginBase]: List of all plugins.
        """
        return list(self.plugins.values())