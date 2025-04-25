"""
Consultant guidelines plugin for Task Manager.
Enforces consultant best practices in task management.
"""
import os
from typing import Dict, List, Any, Optional

from core.adapters.plugin_base import PluginBase
from core.models.task import Task

class ConsultantGuidelinesPlugin(PluginBase):
    """Plugin for enforcing consultant guidelines in task management."""
    
    def __init__(self, config=None):
        """
        Initialize the plugin.
        
        Args:
            config: Configuration dictionary.
        """
        super().__init__(config)
        self.guidelines = []
        self.guideline_source = self.config.get('guideline_source', 'file')
        self.guideline_file = self.config.get('guideline_file', 'plugins/guidelines/consultant_guidelines.txt')
        
    def initialize(self):
        """
        Initialize the plugin by loading guidelines.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        try:
            self.guidelines = self._load_guidelines()
            return len(self.guidelines) > 0
        except Exception as e:
            print(f"Error initializing ConsultantGuidelinesPlugin: {e}")
            return False
    
    def _load_guidelines(self) -> List[Dict[str, Any]]:
        """
        Load guidelines from the configured source.
        
        Returns:
            List[Dict[str, Any]]: List of guideline dictionaries.
        """
        if self.guideline_source == 'embedded':
            return self._get_embedded_guidelines()
        elif self.guideline_source == 'file':
            return self._load_from_file(self.guideline_file)
        else:
            print(f"Unknown guideline source: {self.guideline_source}")
            return []
    
    def _get_embedded_guidelines(self) -> List[Dict[str, Any]]:
        """
        Get the embedded consultant guidelines.
        
        Returns:
            List[Dict[str, Any]]: List of guideline dictionaries.
        """
        # This is a starter set of guidelines that can be expanded
        return [
            {
                "id": "documentation",
                "category": "Project Management",
                "title": "Documentation Standard",
                "description": "All tasks should include appropriate documentation with context, purpose, and outcomes.",
                "check": lambda task: len(task.description) >= 20 and ":" in task.description
            },
            {
                "id": "clarity",
                "category": "Communication",
                "title": "Task Clarity",
                "description": "Task descriptions should clearly state the action taken or required.",
                "check": lambda task: any(verb in task.description.lower() for verb in [
                    "created", "developed", "analyzed", "prepared", "reviewed", 
                    "completed", "implemented", "designed", "tested"
                ])
            },
            {
                "id": "categorization",
                "category": "Organization",
                "title": "Proper Categorization",
                "description": "All tasks must have a specific project category assigned.",
                "check": lambda task: task.category != "Uncategorized" and len(task.category) > 0
            }
        ]
    
    def _load_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load guidelines from a file.
        
        Args:
            file_path: Path to the guideline file.
            
        Returns:
            List[Dict[str, Any]]: List of guideline dictionaries.
        """
        if not os.path.exists(file_path):
            print(f"Guideline file not found: {file_path}")
            return self._get_embedded_guidelines()
            
        try:
            guidelines = []
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Parse the file format - this is a simple implementation
            # The file should have sections separated by ---
            sections = content.split('---')
            
            for section in sections:
                if not section.strip():
                    continue
                    
                lines = section.strip().split('\n')
                if len(lines) < 3:
                    continue
                    
                guideline = {
                    "id": lines[0].strip(),
                    "category": lines[1].strip(),
                    "title": lines[2].strip(),
                    "description": '\n'.join(lines[3:]).strip()
                }
                
                guidelines.append(guideline)
                
            return guidelines if guidelines else self._get_embedded_guidelines()
            
        except Exception as e:
            print(f"Error loading guidelines from file: {e}")
            return self._get_embedded_guidelines()
    
    def check_task(self, task: Task) -> Dict[str, Any]:
        """
        Check a task against consultant guidelines.
        
        Args:
            task: The task to check.
            
        Returns:
            Dict[str, Any]: Analysis results with violations and suggestions.
        """
        violations = []
        suggestions = []
        
        # Check against each guideline
        for guideline in self.guidelines:
            # If the guideline has a check function, use it
            if "check" in guideline and callable(guideline["check"]):
                if not guideline["check"](task):
                    violations.append(guideline["id"])
                    suggestions.append({
                        "guideline": guideline["title"],
                        "suggestion": f"Improve: {guideline['description']}"
                    })
            # Otherwise, use a simple text search (this could be enhanced with AI)
            else:
                # Example: check if any key terms from the description are in the task
                key_terms = guideline.get("key_terms", [])
                if key_terms and not any(term.lower() in task.description.lower() for term in key_terms):
                    violations.append(guideline["id"])
                    suggestions.append({
                        "guideline": guideline["title"],
                        "suggestion": f"Consider: {guideline['description']}"
                    })
        
        # Calculate adherence score
        adherence_score = 1.0 - (len(violations) / max(len(self.guidelines), 1))
        
        return {
            "task_id": task.id,
            "task_description": task.description,
            "adherence_score": adherence_score,
            "violations": violations,
            "suggestions": suggestions,
            "passes_guidelines": len(violations) == 0
        }
    
    def suggest_improvements(self, task: Task) -> List[str]:
        """
        Suggest improvements to make task adhere to guidelines.
        
        Args:
            task: The task to suggest improvements for.
            
        Returns:
            List[str]: List of improvement suggestions.
        """
        analysis = self.check_task(task)
        
        if analysis['adherence_score'] < 0.8:  # Threshold for suggestions
            return [s['suggestion'] for s in analysis['suggestions']]
        return []