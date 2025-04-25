"""
Base plugin system for Task Manager.
Provides the foundation for all plugin extensions.
"""

class PluginBase:
    """Base class for all plugins."""
    
    def __init__(self, config=None):
        """
        Initialize the plugin with configuration.
        
        Args:
            config (dict): Configuration parameters for the plugin.
        """
        self.config = config or {}
        self.enabled = True
        
    def initialize(self):
        """
        Set up the plugin. Called when the plugin is first loaded.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        return True
        
    def shutdown(self):
        """
        Clean up resources. Called when the plugin is being unloaded.
        
        Returns:
            bool: True if shutdown was successful, False otherwise.
        """
        return True
    
    def enable(self):
        """Enable the plugin."""
        self.enabled = True
        
    def disable(self):
        """Disable the plugin."""
        self.enabled = False
        
    @property
    def id(self):
        """
        Unique identifier for this plugin.
        
        Returns:
            str: The plugin identifier.
        """
        return self.__class__.__name__
    
    @property
    def name(self):
        """
        Human-readable name for this plugin.
        
        Returns:
            str: The plugin name.
        """
        return self.config.get('name', self.id)
    
    @property
    def description(self):
        """
        Description of what this plugin does.
        
        Returns:
            str: The plugin description.
        """
        return self.config.get('description', '')
    
    def __str__(self):
        """String representation of the plugin."""
        status = "enabled" if self.enabled else "disabled"
        return f"{self.name} ({self.id}) - {status}"