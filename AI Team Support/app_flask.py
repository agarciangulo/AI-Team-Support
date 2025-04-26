"""
Alternative web application version using Flask instead of Gradio.
This provides a more traditional web interface that can be hosted as a regular web application.
"""
import os
import sys
import subprocess
import traceback
from datetime import datetime, timedelta
import pandas as pd
# Import from the new structure
from core.adapters.notion_adapter import NotionAdapter
from plugins import initialize_all_plugins, plugin_manager  # Add plugin_manager here

# Import from the config
from config import DEBUG_MODE

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

# For the dashboard
from core.ai.analyzers import TaskAnalyzer, ProjectAnalyzer

# Initialize plugins
initialize_all_plugins()

# Initialize Flask app
app = Flask(__name__, 
            static_folder="static",
            template_folder="templates")

@app.route('/')
def index():
    """Render main page."""
    categories = list_all_categories()
    return render_template('index.html', categories=categories)

@app.route('/dashboard')
def dashboard():
    """Render dashboard page."""
    categories = list_all_categories()
    return render_template('dashboard.html', categories=categories)

@app.route('/api/dashboard_data')
def api_dashboard_data():
    """API endpoint to get dashboard data with filtering support."""
    try:
        # Get filter parameters
        employee_filter = request.args.get('employee', 'all')
        project_filter = request.args.get('project', 'all')
        
        # Get all tasks
        df = fetch_notion_tasks()
        
        # Apply filters
        filtered_df = df.copy()
        
        if employee_filter != 'all':
            filtered_df = filtered_df[filtered_df['employee'] == employee_filter]
            
        if project_filter != 'all':
            filtered_df = filtered_df[filtered_df['category'] == project_filter]
        
        # Calculate overall metrics
        total_tasks = len(filtered_df)
        completed_tasks = len(filtered_df[filtered_df['status'] == 'Completed'])
        in_progress_tasks = len(filtered_df[filtered_df['status'] == 'In Progress'])
        pending_tasks = len(filtered_df[filtered_df['status'] == 'Pending'])
        blocked_tasks = len(filtered_df[filtered_df['status'] == 'Blocked'])
        
        completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
        
        # Calculate tasks by category
        category_counts = filtered_df['category'].value_counts().to_dict()
        
        # Calculate task trend (completed tasks over time)
        # Make sure to handle date conversion properly
        filtered_df['date'] = pd.to_datetime(filtered_df['date'])
        df_completed = filtered_df[filtered_df['status'] == 'Completed']
        
        # Group by date and count
        if not df_completed.empty:
            trend_data = df_completed.groupby(df_completed['date'].dt.strftime('%Y-%m-%d')).size().to_dict()
            # Sort by date
            trend_data = {k: trend_data[k] for k in sorted(trend_data.keys())}
        else:
            trend_data = {}
        
        # Calculate project health scores
        project_health = {}
        
        # Use only the filtered dataframe when calculating project health
        if project_filter != 'all':
            # If filtering by project, only calculate health for that project
            categories = [project_filter]
        else:
            # Otherwise, get all unique categories from the filtered dataframe
            categories = filtered_df['category'].unique()
        
        from core.ai.analyzers import ProjectAnalyzer
        analyzer = ProjectAnalyzer()
        
        for category in categories:
            if not category or category == '':
                continue
                
            # For project health, we need to consider all tasks in that project
            # (not just the filtered employee's tasks)
            if employee_filter != 'all':
                # When filtering by employee, show the project health of the
                # projects they're working on, but based on all tasks in that project
                category_tasks = df[df['category'] == category]
            else:
                category_tasks = filtered_df[filtered_df['category'] == category]
                
            if len(category_tasks) > 0:
                health_check = analyzer.analyze(category_tasks, category, "health_check")
                project_health[category] = {
                    "score": round(health_check.get("health_score", 50), 1),
                    "status": health_check.get("health_status", "Unknown"),
                    "task_count": health_check.get("task_count", 0)
                }
        
        # Employee productivity
        employee_stats = {}
        
        # Use the original dataframe to get all employees for the dropdown
        all_employees = df['employee'].unique().tolist()
        all_employees = [e for e in all_employees if e and e.strip()]
        
        # If filtering by employee, only show that employee's stats
        if employee_filter != 'all':
            employees = [employee_filter]
        elif employee_filter == 'all' and project_filter != 'all':
            # If filtering by project, only show employees in that project
            employees = filtered_df['employee'].unique()
        else:
            # Otherwise, show all employees
            employees = filtered_df['employee'].unique()
        
        for employee in employees:
            if not employee or employee == '':
                continue
                
            employee_tasks = filtered_df[filtered_df['employee'] == employee]
            completed = len(employee_tasks[employee_tasks['status'] == 'Completed'])
            total = len(employee_tasks)
            
            employee_stats[employee] = {
                "total_tasks": total,
                "completed_tasks": completed,
                "completion_rate": round((completed / total * 100), 1) if total > 0 else 0
            }
        
        # Get all categories for the dropdown
        all_categories = df['category'].unique().tolist()
        all_categories = [c for c in all_categories if c and c.strip()]
        
        return jsonify({
            'success': True,
            'metrics': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'in_progress_tasks': in_progress_tasks,
                'pending_tasks': pending_tasks,
                'blocked_tasks': blocked_tasks,
                'completion_rate': completion_rate
            },
            'trend_data': trend_data,
            'category_data': category_counts,
            'project_health': project_health,
            'employee_stats': employee_stats,
            'all_employees': all_employees,
            'all_categories': all_categories,
            'filters': {
                'employee': employee_filter,
                'project': project_filter
            }
        })
        
    except Exception as e:
        print(f"Error in dashboard_data: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f"Error generating dashboard data: {e}"
        })

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
