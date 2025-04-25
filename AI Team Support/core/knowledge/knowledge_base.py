"""
Knowledge base management for Task Manager.
Handles storing and retrieving reference information.
"""
import os
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

class KnowledgeBase:
    """Base class for managing domain-specific knowledge."""
    
    def __init__(self, 
                 name: str,
                 source_type: str = "file", 
                 source_location: Optional[str] = None,
                 embedding_model: str = "text-embedding-ada-002"):
        """
        Initialize the knowledge base.
        
        Args:
            name: Name of the knowledge base.
            source_type: Type of source ('file', 'database', 'api', 'embedded').
            source_location: Location of the source.
            embedding_model: Name of the embedding model to use.
        """
        self.name = name
        self.source_type = source_type
        self.source_location = source_location
        self.embedding_model = embedding_model
        self.content = None
        self.sections = []
        self.embeddings = {}
        self.last_loaded = None
        
    def load(self) -> bool:
        """
        Load the knowledge base.
        
        Returns:
            bool: True if loading was successful, False otherwise.
        """
        try:
            if self.source_type == "file":
                return self._load_from_file()
            elif self.source_type == "embedded":
                return self._load_embedded()
            else:
                print(f"Unsupported source type: {self.source_type}")
                return False
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            return False
    
    def _load_from_file(self) -> bool:
        """
        Load knowledge base from a file.
        
        Returns:
            bool: True if loading was successful, False otherwise.
        """
        if not self.source_location or not os.path.exists(self.source_location):
            print(f"Knowledge base file not found: {self.source_location}")
            return False
            
        try:
            with open(self.source_location, "r") as f:
                self.content = f.read()
                
            # Split the content into sections
            self._parse_sections()
            
            self.last_loaded = datetime.now()
            return True
        except Exception as e:
            print(f"Error loading knowledge base from file: {e}")
            return False
    
    def _load_embedded(self) -> bool:
        """
        Load embedded knowledge base.
        
        Returns:
            bool: True if loading was successful, False otherwise.
        """
        # This method should be overridden by subclasses
        print("No embedded content defined. Override this method in a subclass.")
        return False
    
    def _parse_sections(self):
        """Parse the content into sections for easier reference."""
        if not self.content:
            self.sections = []
            return
            
        # Default implementation splits by headers (lines starting with #)
        lines = self.content.split('\n')
        sections = []
        current_section = {"title": "Introduction", "content": ""}
        
        for line in lines:
            if line.startswith('#'):
                if current_section["content"]:
                    sections.append(current_section)
                    
                # Count the number of # to determine the heading level
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break
                        
                title = line[level:].strip()
                current_section = {"title": title, "level": level, "content": ""}
            else:
                current_section["content"] += line + "\n"
        
        # Add the last section
        if current_section["content"]:
            sections.append(current_section)
            
        self.sections = sections
    
    def create_embeddings(self, force: bool = False) -> bool:
        """
        Create embeddings for the knowledge base content.
        
        Args:
            force: If True, recreates all embeddings even if they exist.
            
        Returns:
            bool: True if embedding creation was successful, False otherwise.
        """
        # This requires integration with the OpenAI client
        # For now, we'll just log that embeddings would be created
        print(f"Would create embeddings for {len(self.sections)} sections using {self.embedding_model}")
        return True
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for relevant information.
        
        Args:
            query: The search query.
            top_k: Number of top results to return.
            
        Returns:
            List[Dict[str, Any]]: List of search results.
        """
        # Simple text search as a fallback
        results = []
        query_lower = query.lower()
        
        for section in self.sections:
            if query_lower in section["title"].lower() or query_lower in section["content"].lower():
                score = 0
                if query_lower in section["title"].lower():
                    score += 0.5
                    
                # Count occurrences in content
                score += section["content"].lower().count(query_lower) * 0.1
                
                results.append({
                    "title": section["title"],
                    "content": section["content"][:200] + "..." if len(section["content"]) > 200 else section["content"],
                    "score": score
                })
        
        # Sort by score and limit to top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def get_section(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific section by title.
        
        Args:
            title: Title of the section to retrieve.
            
        Returns:
            Optional[Dict[str, Any]]: The section, or None if not found.
        """
        for section in self.sections:
            if section["title"].lower() == title.lower():
                return section
        return None
    
    def get_all_sections(self) -> List[Dict[str, Any]]:
        """
        Get all sections.
        
        Returns:
            List[Dict[str, Any]]: List of all sections.
        """
        return self.sections
    
    def reload(self) -> bool:
        """
        Reload the knowledge base from its source.
        
        Returns:
            bool: True if reloading was successful, False otherwise.
        """
        # Clear current data
        self.content = None
        self.sections = []
        self.embeddings = {}
        
        # Reload from source
        return self.load()
    
    def get_last_loaded(self) -> Optional[datetime]:
        """
        Get the time when the knowledge base was last loaded.
        
        Returns:
            Optional[datetime]: The time, or None if not loaded.
        """
        return self.last_loaded