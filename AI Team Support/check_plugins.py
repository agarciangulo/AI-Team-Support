#!/usr/bin/env python3
"""
Debug script to check plugin discovery and registration.
Run this script from your project root to check if plugins are working.
"""
import os
import sys

print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

# Check for plugin directories
print("\nChecking plugin directories:")
plugin_dirs = [
    'plugins/guidelines',
    'plugins/feedback',
    'plugins/integrations',
    'plugins/security'
]

for plugin_dir in plugin_dirs:
    print(f"Directory '{plugin_dir}' exists: {os.path.exists(plugin_dir)}")
    if os.path.exists(plugin_dir):
        print(f"  Contents: {os.listdir(plugin_dir)}")

# Try to import the plugin manager
print("\nAttempting to import plugin manager:")
try:
    from core.adapters.plugin_manager import PluginManager
    print("✅ Successfully imported PluginManager")
    
    # Try to create plugin manager instance
    try:
        plugin_manager = PluginManager()
        print("✅ Successfully created PluginManager instance")
        
        # Try discovering plugins
        print("\nAttempting to discover plugins:")
        plugin_manager.discover_plugins(plugin_dirs)
        print(f"Discovered plugin classes: {plugin_manager.plugin_classes}")
        
        # Try importing security plugin directly
        print("\nAttempting to import security plugin directly:")
        try:
            from plugins.security.project_protection import ProjectProtectionPlugin
            print("✅ Successfully imported ProjectProtectionPlugin")
            
            # Try creating an instance of the plugin
            try:
                plugin = ProjectProtectionPlugin()
                print("✅ Successfully created ProjectProtectionPlugin instance")
                print(f"Plugin ID: {plugin.id}")
                print(f"Plugin enabled: {plugin.enabled}")
                
                # Try registering this plugin
                print("\nAttempting to register plugin:")
                if plugin_manager.register_plugin(ProjectProtectionPlugin):
                    print("✅ Successfully registered plugin")
                    
                    # Try getting the registered plugin
                    plugin = plugin_manager.get_plugin('ProjectProtectionPlugin')
                    if plugin:
                        print("✅ Successfully retrieved plugin")
                        print(f"Retrieved plugin: {plugin}")
                    else:
                        print("❌ Failed to retrieve plugin")
                else:
                    print("❌ Failed to register plugin")
                
            except Exception as e:
                print(f"❌ Error creating plugin instance: {e}")
        except ImportError as e:
            print(f"❌ Error importing ProjectProtectionPlugin: {e}")
            
    except Exception as e:
        print(f"❌ Error creating PluginManager: {e}")
except ImportError as e:
    print(f"❌ Error importing PluginManager: {e}")

# Try to import plugins directly
print("\nAttempting to import plugins package:")
try:
    import plugins
    print("✅ Successfully imported plugins package")
    
    # Check for initialize_all_plugins function
    if hasattr(plugins, 'initialize_all_plugins'):
        print("✅ initialize_all_plugins function exists")
        
        # Try running initialize_all_plugins
        print("\nAttempting to initialize all plugins:")
        try:
            plugins.initialize_all_plugins()
            print("✅ Successfully initialized plugins")
            
            # Check if plugin_manager is available
            if hasattr(plugins, 'plugin_manager'):
                print("✅ plugin_manager is available")
                
                # Try getting all plugins
                all_plugins = plugins.plugin_manager.get_all_plugins()
                print(f"All plugins: {all_plugins}")
                
                # Try getting security plugin
                security_plugin = plugins.plugin_manager.get_plugin('ProjectProtectionPlugin')
                if security_plugin:
                    print("✅ Successfully retrieved security plugin")
                    print(f"Security plugin: {security_plugin}")
                    print(f"Security plugin enabled: {security_plugin.enabled}")
                else:
                    print("❌ Security plugin not found")
            else:
                print("❌ plugin_manager not available in plugins module")
                
        except Exception as e:
            print(f"❌ Error initializing plugins: {e}")
    else:
        print("❌ initialize_all_plugins function not found")
        
except ImportError as e:
    print(f"❌ Error importing plugins package: {e}")

print("\nDebug script completed")