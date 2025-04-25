"""
Task data model for Task Manager.
Defines the structure and behavior of task objects.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

class TaskStatus(Enum):
    """Enumeration of possible task statuses."""
    COMPLETED = "Completed"
    IN_PROGRESS = "In Progress"
    PENDING = "Pending"
    BLOCKED = "Blocked"
    
    @classmethod
    def from_string(cls, status_str: str) -> 'TaskStatus':
        """
        Convert a string to a TaskStatus enum value.
        
        Args:
            status_str: String representation of the status.
            
        Returns:
            TaskStatus: The corresponding enum value.
            
        Raises:
            ValueError: If the string doesn't match any status.
        """
        status_map = {
            "completed": cls.COMPLETED,
            "in progress": cls.IN_PROGRESS,
            "pending": cls.PENDING,
            "blocked": cls.BLOCKED
        }
        
        normalized = status_str.lower().strip()
        
        if normalized in status_map:
            return status_map[normalized]
        
        # Try to match partial status names
        for key, value in status_map.items():
            if key in normalized:
                return value
        
        # Default to PENDING if no match
        return cls.PENDING

class Task:
    """Represents a task in the system."""
    
    def __init__(self, 
                 description: str,
                 status: str = "Pending",
                 employee: str = "",
                 date: Optional[str] = None,
                 category: str = "Uncategorized",
                 task_id: Optional[str] = None,
                 reminder_sent: bool = False,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a task object.
        
        Args:
            description: The task description.
            status: The task status.
            employee: The employee assigned to the task.
            date: The date of the task (YYYY-MM-DD).
            category: The task category.
            task_id: The unique identifier for the task.
            reminder_sent: Whether a reminder has been sent for this task.
            metadata: Additional metadata for the task.
        """
        self.description = description
        self._status = TaskStatus.from_string(status)
        self.employee = employee
        
        # Handle date
        if date is None:
            self.date = datetime.now().strftime("%Y-%m-%d")
        elif isinstance(date, datetime):
            self.date = date.strftime("%Y-%m-%d")
        else:
            self.date = date
            
        self.category = category
        self.id = task_id
        self.reminder_sent = reminder_sent
        self.metadata = metadata or {}
        
        # Calculated fields
        self._days_old = None
        
    @property
    def status(self) -> str:
        """Get the string representation of the task status."""
        return self._status.value
    
    @status.setter
    def status(self, value: str):
        """Set the task status from a string."""
        self._status = TaskStatus.from_string(value)
    
    @property
    def days_old(self) -> int:
        """
        Get the number of days since the task date.
        
        Returns:
            int: Number of days.
        """
        if self._days_old is not None:
            return self._days_old
            
        try:
            task_date = datetime.strptime(self.date, "%Y-%m-%d")
            delta = datetime.now() - task_date
            return delta.days
        except (ValueError, TypeError):
            return 0
    
    @days_old.setter
    def days_old(self, value: int):
        """Set the days_old value directly."""
        self._days_old = value
    
    @property
    def is_completed(self) -> bool:
        """Check if the task is completed."""
        return self._status == TaskStatus.COMPLETED
    
    @property
    def is_blocked(self) -> bool:
        """Check if the task is blocked."""
        return self._status == TaskStatus.BLOCKED
    
    @property
    def needs_reminder(self) -> bool:
        """Check if the task needs a reminder."""
        return (not self.is_completed and 
                not self.reminder_sent and 
                self.days_old > 2)  # Using 2 as a default threshold
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        Create a Task object from a dictionary.
        
        Args:
            data: Dictionary containing task data.
            
        Returns:
            Task: A new Task object.
        """
        task_data = {
            "description": data.get("task", ""),
            "status": data.get("status", "Pending"),
            "employee": data.get("employee", ""),
            "date": data.get("date"),
            "category": data.get("category", "Uncategorized"),
            "task_id": data.get("id"),
            "reminder_sent": data.get("reminder_sent", False)
        }
        
        # Handle extra fields as metadata
        metadata = {}
        for key, value in data.items():
            if key not in ["task", "status", "employee", "date", "category", "id", "reminder_sent"]:
                metadata[key] = value
                
        if metadata:
            task_data["metadata"] = metadata
            
        task = cls(**task_data)
        
        # Set days_old if available
        if "days_old" in data:
            task.days_old = data["days_old"]
            
        return task
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Task object to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the task.
        """
        result = {
            "task": self.description,
            "status": self.status,
            "employee": self.employee,
            "date": self.date,
            "category": self.category,
            "reminder_sent": self.reminder_sent
        }
        
        if self.id:
            result["id"] = self.id
            
        if self._days_old is not None:
            result["days_old"] = self._days_old
            
        # Add metadata
        result.update(self.metadata)
        
        return result
    
    def __str__(self) -> str:
        """String representation of the task."""
        return f"{self.description} ({self.status}) - {self.employee}"
    
    def __repr__(self) -> str:
        """Detailed representation of the task."""
        return f"Task(description='{self.description}', status='{self.status}', employee='{self.employee}', date='{self.date}', category='{self.category}')"