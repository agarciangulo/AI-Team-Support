"""
Simplified security manager for Task Manager.
Handles tokenization and protection of sensitive information.
This version does not require the cryptography package.
"""
import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Union, Tuple

class SecurityManager:
    """
    Manages security features for sensitive data.
    
    This class provides functionality to protect sensitive information
    like project names before they're sent to external services.
    """
    
    def __init__(self, token_file_path: str = "security_tokens.json"):
        """
        Initialize the security manager.
        
        Args:
            token_file_path: Path to the token mapping file.
        """
        self.token_file_path = token_file_path
        self.token_map = {}
        self.reverse_map = {}
        
        # Load any existing token mappings
        self._load_tokens()
    
    def _load_tokens(self) -> None:
        """Load token mappings from file if it exists."""
        if os.path.exists(self.token_file_path):
            try:
                with open(self.token_file_path, 'r') as f:
                    stored_data = json.load(f)
                    self.token_map = stored_data.get('token_map', {})
                    # Also build the reverse mapping
                    self.reverse_map = {v: k for k, v in self.token_map.items()}
            except Exception as e:
                print(f"Error loading token mappings: {e}")
                # Initialize with empty mappings if loading fails
                self.token_map = {}
                self.reverse_map = {}
    
    def _save_tokens(self) -> None:
        """Save token mappings to file."""
        try:
            with open(self.token_file_path, 'w') as f:
                json.dump({
                    'token_map': self.token_map
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving token mappings: {e}")
    
    def _generate_token(self, project_name: str) -> str:
        """
        Generate a token for a project name.
        
        Args:
            project_name: The real project name.
            
        Returns:
            str: The token.
        """
        # Create a hash of the project name
        hash_obj = hashlib.md5(project_name.encode())
        hash_str = hash_obj.hexdigest()[:8]  # Use first 8 chars of hash
        
        # Create a token with a prefix for clarity
        return f"PROJ_{hash_str}"
    
    def tokenize_project(self, project_name: str) -> str:
        """
        Replace a project name with a token.
        
        Args:
            project_name: The real project name.
            
        Returns:
            str: The token that replaces the project name.
        """
        if not project_name or project_name.lower() == "uncategorized":
            return project_name
            
        # Check if we already have a token for this project
        if project_name in self.token_map:
            return self.token_map[project_name]
            
        # Generate a new token
        token = self._generate_token(project_name)
        
        # Handle collisions (unlikely but possible)
        while token in self.reverse_map:
            token = token + "_" + hashlib.md5(os.urandom(8)).hexdigest()[:4]
        
        # Store the mapping
        self.token_map[project_name] = token
        self.reverse_map[token] = project_name
        
        # Save the updated mappings
        self._save_tokens()
        
        return token
    
    def detokenize_project(self, token: str) -> str:
        """
        Replace a token with the original project name.
        
        Args:
            token: The token to convert back.
            
        Returns:
            str: The original project name.
        """
        # If it's not a token or not in our mapping, return as is
        if not token or not isinstance(token, str) or not token.startswith("PROJ_"):
            return token
            
        # Look up the original project name
        return self.reverse_map.get(token, token)
    
    def protect_task_data(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Protect sensitive information in a task dictionary.
        
        Args:
            task_data: The task data dictionary.
            
        Returns:
            Dict[str, Any]: Protected task data.
        """
        protected = task_data.copy()
        
        # Tokenize the category/project
        if 'category' in protected and protected['category']:
            protected['category'] = self.tokenize_project(protected['category'])
        
        # Also look for project mentions in the task description
        if 'task' in protected and protected['task']:
            # This is a simplified approach - for production, you'd want
            # a more sophisticated detection of project names in text
            for project_name in self.token_map.keys():
                if project_name in protected['task']:
                    token = self.token_map[project_name]
                    protected['task'] = protected['task'].replace(project_name, token)
        
        return protected
    
    def unprotect_task_data(self, protected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore original sensitive information in a task dictionary.
        
        Args:
            protected_data: The protected task data.
            
        Returns:
            Dict[str, Any]: Original task data.
        """
        original = protected_data.copy()
        
        # Detokenize the category/project
        if 'category' in original and original['category']:
            original['category'] = self.detokenize_project(original['category'])
        
        # Also restore project mentions in the task description
        if 'task' in original and original['task']:
            # Replace any tokens with their original project names
            for token, project_name in self.reverse_map.items():
                if token in original['task']:
                    original['task'] = original['task'].replace(token, project_name)
        
        return original
    
    def protect_task_list(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Protect sensitive information in a list of tasks.
        
        Args:
            tasks: List of task dictionaries.
            
        Returns:
            List[Dict[str, Any]]: Protected task list.
        """
        return [self.protect_task_data(task) for task in tasks]
    
    def unprotect_task_list(self, protected_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Restore original sensitive information in a list of tasks.
        
        Args:
            protected_tasks: List of protected task dictionaries.
            
        Returns:
            List[Dict[str, Any]]: Original task list.
        """
        return [self.unprotect_task_data(task) for task in protected_tasks]
    
    def protect_text(self, text: str) -> str:
        """
        Protect sensitive information in text.
        
        Args:
            text: The original text.
            
        Returns:
            str: Protected text.
        """
        protected = text
        
        # Replace project names with tokens
        for project_name, token in self.token_map.items():
            protected = protected.replace(project_name, token)
        
        return protected
    
    def unprotect_text(self, protected_text: str) -> str:
        """
        Restore original sensitive information in text.
        
        Args:
            protected_text: The protected text.
            
        Returns:
            str: Original text.
        """
        text = protected_text
        
        # Replace tokens with project names
        for token, project_name in self.reverse_map.items():
            text = text.replace(token, project_name)
        
        return text