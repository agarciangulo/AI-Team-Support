"""
Plugin configuration for Task Manager.
"""
from core.adapters.plugin_manager import PluginManager

# Initialize plugin manager
plugin_manager = PluginManager()

# Define plugin directories to search
PLUGIN_DIRECTORIES = [
    'plugins/guidelines',
    'plugins/feedback',
    'plugins/integrations',
    'plugins/security'  # Add security plugins directory
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
    },
    'ProjectProtectionPlugin': {  # Add the new security plugin
        'token_file_path': 'security_tokens.json',
        'enabled': True,
        'name': 'Project Protection'
    }
}

def initialize_all_plugins():
    """
    Initialize all configured plugins.
    """
    # Import config to get database IDs
    from config import NOTION_FEEDBACK_DB_ID
    
    # Update feedback DB ID
    if 'PeerFeedbackPlugin' in PLUGIN_CONFIGS:
        PLUGIN_CONFIGS['PeerFeedbackPlugin']['feedback_database_id'] = NOTION_FEEDBACK_DB_ID
    
    print("\nRegistering plugins...")
    # Register plugins
    registered_plugins = []
    for plugin_name, config in PLUGIN_CONFIGS.items():
        print(f"Attempting to register {plugin_name}")
        if plugin_manager.register_plugin_by_name(plugin_name, config):
            registered_plugins.append(plugin_name)
            print(f"✅ Successfully registered {plugin_name}")
        else:
            print(f"❌ Failed to register {plugin_name}")
    
    print(f"Registered plugins: {', '.join(registered_plugins)}")
    
    # Debug output of all available plugins
    all_plugins = plugin_manager.get_all_plugins()
    print(f"All plugins after registration: {all_plugins}")
    
    for plugin in all_plugins:
        print(f"Plugin {plugin.id}: enabled={plugin.enabled}")
    
    return registered_plugins
