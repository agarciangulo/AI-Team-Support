"""
Project name protection plugin for Task Manager.
Handles tokenization of project names for security.
This version does not require the cryptography package.
"""
from typing import Dict, List, Any, Optional
from core.adapters.plugin_base import PluginBase
from core.security.security_manager import SecurityManager

class ProjectProtectionPlugin(PluginBase):
    """Plugin for protecting sensitive project names."""
    
    def __init__(self, config=None):
        """
        Initialize the plugin.
        
        Args:
            config: Configuration dictionary.
        """
        super().__init__(config)
        
        # Initialize the security manager
        token_file = self.config.get('token_file_path', 'security_tokens.json')
        
        self.security_manager = SecurityManager(token_file)
        self.enabled = self.config.get('enabled', True)
    
    def initialize(self):
        """
        Initialize the plugin.
        
        Returns:
            bool: True if initialization was successful.
        """
        # Nothing special needed for initialization
        return True
    
    def protect_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Protect sensitive information in a task.
        
        Args:
            task: The task dictionary.
            
        Returns:
            Dict[str, Any]: Protected task.
        """
        if not self.enabled:
            return task
            
        return self.security_manager.protect_task_data(task)
    
    def unprotect_task(self, protected_task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore original information in a protected task.
        
        Args:
            protected_task: The protected task dictionary.
            
        Returns:
            Dict[str, Any]: Original task.
        """
        if not self.enabled:
            return protected_task
            
        return self.security_manager.unprotect_task_data(protected_task)
    
    def protect_task_list(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Protect sensitive information in a list of tasks.
        
        Args:
            tasks: List of task dictionaries.
            
        Returns:
            List[Dict[str, Any]]: Protected task list.
        """
        if not self.enabled:
            return tasks
            
        return self.security_manager.protect_task_list(tasks)
    
    def unprotect_task_list(self, protected_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Restore original information in a list of protected tasks.
        
        Args:
            protected_tasks: List of protected task dictionaries.
            
        Returns:
            List[Dict[str, Any]]: Original task list.
        """
        if not self.enabled:
            return protected_tasks
            
        return self.security_manager.unprotect_task_list(protected_tasks)
    
    def protect_text(self, text: str) -> str:
        """
        Protect sensitive information in text.
        
        Args:
            text: The original text.
            
        Returns:
            str: Protected text.
        """
        if not self.enabled:
            return text
            
        return self.security_manager.protect_text(text)
    
    def unprotect_text(self, protected_text: str) -> str:
        """
        Restore original information in protected text.
        
        Args:
            protected_text: The protected text.
            
        Returns:
            str: Original text.
        """
        if not self.enabled:
            return protected_text
            
        return self.security_manager.unprotect_text(protected_text)