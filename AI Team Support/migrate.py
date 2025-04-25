#!/usr/bin/env python3
"""
Migration script to setup the new framework structure and create compatibility bridges.
This script will:
1. Create the new directory structure
2. Initialize plugins
3. Create compatibility layers to ensure existing code works with the new structure
"""
import os
import shutil
import importlib
import sys
from pathlib import Path

def create_directory_structure():
    """Create the new directory structure."""
    print("Creating new directory structure...")
    
    # Define directories to create
    directories = [
        # Core components
        'core/adapters',
        'core/ai',
        'core/models',
        'core/knowledge',
        
        # Plugin system
        'plugins/guidelines',
        'plugins/feedback',
        'plugins/integrations',
        
        # Interface components
        'interfaces/web',
        'interfaces/gradio',
        'interfaces/api',
    ]
    
    # Create directories
    for directory in directories:
        full_path = Path(directory)
        
        if not full_path.exists():
            full_path.mkdir(parents=True)
            print(f"Created directory: {full_path}")
        else:
            print(f"Directory already exists: {full_path}")
    
    # Create __init__.py files to make directories packages
    for directory in directories:
        parts = directory.split('/')
        path = Path()
        
        for part in parts:
            path = path / part
            init_file = path / "__init__.py"
            
            if not init_file.exists():
                with open(init_file, 'w') as f:
                    f.write(f'"""\n{part.capitalize()} package for Task Manager.\n"""\n')
                print(f"Created __init__.py in {path}")
                
    print("Directory structure created successfully!")

def create_compatibility_layer():
    """Create compatibility layer to ensure existing code works with the new structure."""
    print("Creating compatibility layer...")
    
    # Create core/__init__.py that exposes old interfaces
    core_init = """\"\"\"
Core package for Task Manager.
This module provides compatibility with the old structure.
\"\"\"
# Import from new locations but expose with old names
from core.adapters.notion_adapter import NotionAdapter

# Create instances with default config for backward compatibility
notion_adapter = NotionAdapter()

# Functions from notion_client.py
fetch_notion_tasks = notion_adapter.fetch_tasks
identify_stale_tasks = notion_adapter.identify_stale_tasks
mark_task_as_reminded = notion_adapter.mark_task_as_reminded
insert_task_to_notion = notion_adapter.insert_task
update_task_in_notion = notion_adapter.update_task
fetch_peer_feedback = notion_adapter.fetch_peer_feedback
list_all_categories = notion_adapter.list_all_categories
validate_notion_connection = notion_adapter.validate_connection
"""
    
    with open(Path('core/__init__.py'), 'w') as f:
        f.write(core_init)
    
    # Add imports to make the new modules available
    with open(Path('core/adapters/__init__.py'), 'w') as f:
        f.write('"""\nAdapters package for Task Manager.\n"""\n')
        f.write('from core.adapters.notion_adapter import NotionAdapter\n')
        f.write('from core.adapters.plugin_base import PluginBase\n')
        f.write('from core.adapters.plugin_manager import PluginManager\n')
    
    print("Compatibility layer created!")

def initialize_plugins():
    """Initialize the plugin system and register core plugins."""
    print("Initializing plugins...")
    
    # Create a basic plugin configuration file
    plugin_config = """\"\"\"
Plugin configuration for Task Manager.
\"\"\"
from core.adapters.plugin_manager import PluginManager

# Initialize plugin manager
plugin_manager = PluginManager()

# Define plugin directories to search
PLUGIN_DIRECTORIES = [
    'plugins/guidelines',
    'plugins/feedback',
    'plugins/integrations'
]

# Discover available plugins
plugin_manager.discover_plugins(PLUGIN_DIRECTORIES)

# Plugin configurations
PLUGIN_CONFIGS = {
    'ConsultantGuidelinesPlugin': {
        'guideline_source': 'embedded',
        'name': 'Consultant Guidelines'
    },
    'PeerFeedbackPlugin': {
        'feedback_database_id': None,  # Will be set from config
        'name': 'Peer Feedback'
    }
}

def initialize_all_plugins():
    \"\"\"
    Initialize all configured plugins.
    \"\"\"
    # Import config to get database IDs
    from config import NOTION_FEEDBACK_DB_ID
    
    # Update feedback DB ID
    if 'PeerFeedbackPlugin' in PLUGIN_CONFIGS:
        PLUGIN_CONFIGS['PeerFeedbackPlugin']['feedback_database_id'] = NOTION_FEEDBACK_DB_ID
    
    # Register plugins
    registered_plugins = []
    for plugin_name, config in PLUGIN_CONFIGS.items():
        if plugin_manager.register_plugin_by_name(plugin_name, config):
            registered_plugins.append(plugin_name)
    
    print(f"Registered plugins: {', '.join(registered_plugins)}")
    return registered_plugins
"""
    
    with open(Path('plugins/__init__.py'), 'w') as f:
        f.write(plugin_config)
    
    print("Plugin initialization code created!")

def update_app_imports():
    """Update imports in app.py to use the new structure."""
    print("Updating app.py imports...")
    
    # Read the current app.py
    try:
        with open('app.py', 'r') as f:
            app_content = f.read()
            
        # Update imports
        import_lines = [
            "# Import from the new structure",
            "from core.adapters.notion_adapter import NotionAdapter",
            "from core.ui.interface import create_ui",
            "# Initialize plugins",
            "from plugins import initialize_all_plugins",
            "# Initialize plugins on startup",
            "initialize_all_plugins()"
        ]
        
        # Find the right place to insert these lines
        import_block_end = app_content.find("from core.notion_client import")
        if import_block_end > 0:
            # Insert our new imports after the existing imports
            updated_content = app_content[:import_block_end] + "\n".join(import_lines) + "\n\n" + app_content[import_block_end:]
            
            # Write back to a new file to be safe
            with open('app_new.py', 'w') as f:
                f.write(updated_content)
                
            print("Updated app.py imports - saved as app_new.py")
        else:
            print("Could not locate import section in app.py")
    
    except Exception as e:
        print(f"Error updating app.py: {e}")

def main():
    """Main migration function."""
    print("Starting migration to new framework structure...")
    
    # Create the directory structure
    create_directory_structure()
    
    # Create compatibility layer
    create_compatibility_layer()
    
    # Initialize plugins
    initialize_plugins()
    
    # Update app imports
    update_app_imports()
    
    print("\nMigration completed!")
    print("\nNext steps:")
    print("1. Review app_new.py and replace app.py if everything looks good")
    print("2. Test the application with the new structure")
    print("3. Gradually migrate more functionality to the new framework")

if __name__ == "__main__":
    main()