"""
Alternative web application version using Flask instead of Gradio.
This provides a more traditional web interface that can be hosted as a regular web application.
"""
import os
import sys
import subprocess

# First make sure setuptools is installed
try:
    import pkg_resources
except ImportError:
    print("Installing setuptools...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools"])
    import pkg_resources
    print("setuptools installed successfully.")

# List of required packages
REQUIRED_PACKAGES = [
    "openai>=1.0.0",  # Using the new OpenAI API
    "notion-client",
    "pandas",
    "python-dateutil",
    "flask",
    "scikit-learn",
    "numpy",
    "python-dotenv"  # For .env file support
]

def install_requirements():
    """Install required packages if not already installed."""
    print("Checking and installing required packages...")
    
    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = []
    
    for package in REQUIRED_PACKAGES:
        package_name = package.split('==')[0] if '==' in package else package
        if package_name.lower() not in installed:
            missing.append(package)
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("All required packages installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing packages: {e}")
            print("Please install the following packages manually:")
            for pkg in missing:
                print(f"  - {pkg}")
            sys.exit(1)
    else:
        print("All required packages already installed.")

# Run the installation function
install_requirements()

from flask import Flask, render_template, request, jsonify
import traceback
from datetime import datetime, timedelta
import pandas as pd

# Import from the new structure
from core.adapters.notion_adapter import NotionAdapter
from plugins import initialize_all_plugins

# Import from the config
from config import DEBUG_MODE

# Import from compatibility layer for now
from core import (
    fetch_notion_tasks, 
    identify_stale_tasks, 
    list_all_categories, 
    fetch_peer_feedback
)

# These will be imported from new modules eventually
from core.task_extractor import extract_tasks_from_update
from core.task_processor import insert_or_update_task

# We'll use these for AI insights
from core.openai_client import (
    get_coaching_insight,
    get_project_insight
)

# Initialize plugins
initialize_all_plugins()

# DEBUG: Check if security plugin is loaded and enabled
print("Checking for security plugin...")
from plugins import plugin_manager
security_plugin = plugin_manager.get_plugin('ProjectProtectionPlugin')
if security_plugin:
    print(f"Security plugin found: {security_plugin}")
    print(f"Security plugin enabled: {security_plugin.enabled}")
    if hasattr(security_plugin, 'security_manager'):
        print(f"Token file path: {security_plugin.security_manager.token_file_path}")
        print(f"Token file exists: {os.path.exists(security_plugin.security_manager.token_file_path)}")
        if os.path.exists(security_plugin.security_manager.token_file_path):
            with open(security_plugin.security_manager.token_file_path, 'r') as f:
                print(f"Token file content: {f.read()}")
    else:
        print("Security manager not initialized properly!")
else:
    print("Security plugin not found! Available plugins:")
    for plugin in plugin_manager.get_all_plugins():
        print(f" - {plugin}")

# Initialize Flask app
app = Flask(__name__, 
            static_folder="static",
            template_folder="templates")

@app.route('/')
def index():
    """Render main page."""
    categories = list_all_categories()
    return render_template('index.html', categories=categories)

@app.route('/api/process_update', methods=['POST'])
def process_update():
    """Process task update from form submission."""
    try:
        # Try to get data from different possible sources
        if request.is_json:
            # If the request has JSON data
            data = request.get_json()
            update_text = data.get('update_text', '')
        elif request.form:
            # If the request has form data
            update_text = request.form.get('update_text', '')
        else:
            # If the request has raw data
            update_text = request.data.decode('utf-8')
            
        print(f"Received update text: {update_text[:100]}...")  # Debug print
            
        if not update_text:
            return jsonify({
                'success': False,
                'message': 'No update text provided'
            })
        
        # Log output for tracking progress
        log_output = []
        log_output.append("⏳ Processing your update...")
        
        # Extract tasks from update text
        tasks = extract_tasks_from_update(update_text)
        
        if not tasks:
            return jsonify({
                'success': False,
                'message': 'No tasks could be extracted from your update. Please check your input and try again.'
            })
            
        log_output.append(f"✅ Extracted {len(tasks)} tasks from your update")
        
        # Get existing tasks from Notion
        log_output.append("⏳ Fetching existing tasks from Notion...")
        existing_tasks = fetch_notion_tasks()
        log_output.append(f"✅ Fetched {len(existing_tasks)} existing tasks")
        
        # Process tasks
        log_output.append("⏳ Processing tasks...")
        
        # DEBUG: Check tasks before processing
        print("Tasks before processing:")
        for i, task in enumerate(tasks):
            print(f"Task {i+1}: {task.get('task', 'Unknown')} - Category: {task.get('category', 'None')}")
        
        for task in tasks:
            # DEBUG: Check if security plugin is working during processing
            security_plugin = plugin_manager.get_plugin('ProjectProtectionPlugin')
            if security_plugin and security_plugin.enabled:
                protected_task = security_plugin.protect_task(task.copy())
                print(f"Original category: {task.get('category', 'None')}")
                print(f"Protected category: {protected_task.get('category', 'None')}")
            
            insert_or_update_task(task, existing_tasks, log_output)
            
        # Get coaching insights
        person_name = ""
        if tasks and isinstance(tasks[0], dict) and "employee" in tasks[0]:
            person_name = tasks[0].get("employee", "")
            
        peer_feedback = []
        if person_name:
            try:
                peer_feedback = fetch_peer_feedback(person_name)
                log_output.append(f"✅ Fetched {len(peer_feedback)} peer feedback entries")
            except Exception as e:
                log_output.append(f"⚠️ Error fetching peer feedback: {e}")
                
        # Get recent tasks
        recent_tasks = pd.DataFrame()
        try:
            recent_tasks = existing_tasks[existing_tasks['date'] >= datetime.now() - timedelta(days=14)]
            log_output.append(f"✅ Retrieved {len(recent_tasks)} recent tasks for analysis")
        except Exception as e:
            log_output.append(f"⚠️ Error retrieving recent tasks: {e}")
            
        # Generate coaching insights
        log_output.append("⏳ Generating coaching insights...")
        try:
            reflection = get_coaching_insight(person_name, tasks, recent_tasks, peer_feedback)
            log_output.append("✅ Generated coaching insights")
        except Exception as e:
            log_output.append(f"⚠️ Error generating coaching insights: {e}")
            reflection = "Unable to generate coaching insights at this time."
            
        # Format tasks for display
        tasks_formatted = []
        for task in tasks:
            if isinstance(task, dict) and "task" in task and "status" in task:
                tasks_formatted.append({
                    'task': task['task'],
                    'status': task['status'],
                    'employee': task.get('employee', ''),
                    'category': task.get('category', '')
                })
                
        # Return JSON response
        return jsonify({
            'success': True,
            'tasks': tasks_formatted,
            'coaching': reflection,
            'logs': log_output if DEBUG_MODE else None
        })
        
    except Exception as e:
        print(f"Error in process_update: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f"Error processing your update: {e}"
        })

@app.route('/api/stale_tasks')
def api_stale_tasks():
    """API endpoint to get stale tasks."""
    try:
        df = fetch_notion_tasks()
        stale = identify_stale_tasks(df)
        
        if stale.empty:
            return jsonify({
                'success': True,
                'has_stale': False,
                'message': 'No overdue tasks!'
            })
            
        # Format stale tasks by employee
        stale_tasks_by_employee = {}
        for _, row in stale.iterrows():
            employee = row['employee']
            if employee not in stale_tasks_by_employee:
                stale_tasks_by_employee[employee] = []
                
            date_str = row['date'].strftime('%Y-%m-%d') if row['date'] else "No date"
            stale_tasks_by_employee[employee].append({
                'task': row['task'],
                'status': row['status'],
                'date': date_str,
                'days_old': row['days_old']
            })
            
        return jsonify({
            'success': True,
            'has_stale': True,
            'tasks_by_employee': stale_tasks_by_employee
        })
        
    except Exception as e:
        print(f"Error in api_stale_tasks: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f"Error checking overdue tasks: {e}"
        })

@app.route('/api/tasks_by_category')
def api_tasks_by_category():
    """API endpoint to get tasks by category."""
    try:
        category = request.args.get('category', '')
        if not category:
            return jsonify({
                'success': False,
                'message': 'No category specified'
            })
            
        df = fetch_notion_tasks()
        filtered = df[(df["category"] == category) & (df["status"] != "Completed")]
        
        if filtered.empty:
            return jsonify({
                'success': True,
                'has_tasks': False,
                'message': f"No open tasks in project '{category}'"
            })
            
        # Format tasks by employee
        tasks_by_employee = {}
        for _, row in filtered.iterrows():
            employee = row['employee']
            if employee not in tasks_by_employee:
                tasks_by_employee[employee] = []
                
            date_str = row['date'].strftime('%Y-%m-%d') if row['date'] else "No date"
            tasks_by_employee[employee].append({
                'task': row['task'],
                'status': row['status'],
                'date': date_str
            })
            
        # Get status summary
        status_summary = filtered["status"].value_counts().to_dict()
        
        # Get AI insight
        try:
            insight = get_project_insight(category, filtered)
        except Exception as e:
            insight = f"Unable to generate AI insight: {e}"
            
        return jsonify({
            'success': True,
            'has_tasks': True,
            'tasks_by_employee': tasks_by_employee,
            'status_summary': status_summary,
            'insight': insight
        })
        
    except Exception as e:
        print(f"Error in api_tasks_by_category: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f"Error getting project tasks: {e}"
        })

@app.route('/api/categories')
def api_categories():
    """API endpoint to get all categories."""
    try:
        categories = list_all_categories()
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        print(f"Error in api_categories: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f"Error fetching categories: {e}"
        })

if __name__ == '__main__':
    # Check if Notion connection is valid before starting the app
    from core.adapters.notion_adapter import NotionAdapter
    notion = NotionAdapter()
    if not notion.validate_connection():
        print("❌ Failed to connect to Notion. Please check your credentials.")
        import sys
        sys.exit(1)
        
    # Start the web application
    app.run(host='0.0.0.0', port=5000, debug=DEBUG_MODE)