"""
Notion API integration for Task Manager.
Handles all interactions with Notion databases.
"""
from notion_client import Client
from datetime import datetime, timedelta
from dateutil import parser
import pandas as pd
import traceback
from typing import List, Dict, Optional, Any, Union

# Import from plugins to access security protection
from plugins import plugin_manager

# Import configuration from the old location for now
# This will be updated later when we migrate the config
from config import (
    NOTION_TOKEN, 
    NOTION_DATABASE_ID, 
    NOTION_FEEDBACK_DB_ID, 
    DEBUG_MODE, 
    DAYS_THRESHOLD
)

class NotionAdapter:
    """Adapter for Notion API integration."""
    
    def __init__(self, token=None, task_db_id=None, feedback_db_id=None):
        """
        Initialize the Notion adapter.
        
        Args:
            token: Notion API token. If None, uses value from config.
            task_db_id: Notion task database ID. If None, uses value from config.
            feedback_db_id: Notion feedback database ID. If None, uses value from config.
        """
        self.token = token or NOTION_TOKEN
        self.task_db_id = task_db_id or NOTION_DATABASE_ID
        self.feedback_db_id = feedback_db_id or NOTION_FEEDBACK_DB_ID
        
        # Initialize Notion client
        self.client = Client(auth=self.token)
    
    def debug_print(self, message):
        """Print debug messages if DEBUG_MODE is True."""
        if DEBUG_MODE:
            print(message)
    
    def validate_connection(self) -> bool:
        """
        Validate connection to Notion API.
        
        Returns:
            bool: True if connection is successful, False otherwise.
        """
        try:
            response = self.client.databases.query(database_id=self.task_db_id, page_size=1)
            print("✅ Notion connection successful!")
            return True
        except Exception as e:
            print(f"❌ Notion connection failed: {e}")
            return False
    
    # Helper functions for safer Notion property access
    def get_title_content(self, props, key):
        """Safely extract title content from Notion properties."""
        try:
            if key in props and props[key]["title"] and len(props[key]["title"]) > 0:
                return props[key]["title"][0]["text"]["content"]
            return ""
        except (KeyError, IndexError):
            return ""

    def get_select_value(self, props, key, default=""):
        """Safely extract select value from Notion properties."""
        try:
            if key in props and props[key].get("select"):
                return props[key]["select"]["name"]
            return default
        except KeyError:
            return default

    def get_rich_text_content(self, props, key):
        """Safely extract rich text content from Notion properties."""
        try:
            if key in props and props[key].get("rich_text") and len(props[key]["rich_text"]) > 0:
                return props[key]["rich_text"][0]["text"]["content"]
            return ""
        except (KeyError, IndexError):
            return ""

    def get_date_value(self, props, key):
        """Safely extract date value from Notion properties."""
        try:
            if key in props and props[key].get("date") and props[key]["date"].get("start"):
                return parser.parse(props[key]["date"]["start"])
            return None
        except (KeyError, ValueError, TypeError):
            return None

    def get_checkbox_value(self, props, key, default=False):
        """Safely extract checkbox value from Notion properties."""
        try:
            if key in props:
                return props[key]["checkbox"]
            return default
        except KeyError:
            return default

    def fetch_tasks(self) -> pd.DataFrame:
        """
        Fetch tasks from Notion with pagination support.
        
        Returns:
            pd.DataFrame: DataFrame containing all tasks.
        """
        all_pages = []
        has_more = True
        start_cursor = None

        while has_more:
            response = self.client.databases.query(
                database_id=self.task_db_id,
                start_cursor=start_cursor,
                page_size=100  # Maximum allowed by Notion API
            )

            all_pages.extend(response["results"])
            has_more = response["has_more"]

            if has_more:
                start_cursor = response["next_cursor"]

        rows = []
        for page in all_pages:
            try:
                props = page["properties"]

                # Use safer property access
                task = {
                    "id": page["id"],
                    "task": self.get_title_content(props, "Task"),
                    "status": self.get_select_value(props, "Status", "No Status"),
                    "employee": self.get_rich_text_content(props, "Employee"),
                    "date": self.get_date_value(props, "Date"),
                    "reminder_sent": self.get_checkbox_value(props, "Reminder Sent", False),
                    "category": self.get_rich_text_content(props, "Category"),
                }
                rows.append(task)
            except Exception as e:
                self.debug_print(f"Error processing Notion page {page['id']}: {e}")
                continue

        tasks_df = pd.DataFrame(rows)
        
        # Get the protection plugin if available
        protection_plugin = plugin_manager.get_plugin('ProjectProtectionPlugin')
        
        # Unprotect task data if necessary
        if protection_plugin and protection_plugin.enabled and not tasks_df.empty:
            try:
                # Convert DataFrame to list of dicts for unprotection
                tasks_list = tasks_df.to_dict('records')
                
                # Unprotect task data
                unprotected_tasks = protection_plugin.unprotect_task_list(tasks_list)
                
                # Convert back to DataFrame
                tasks_df = pd.DataFrame(unprotected_tasks)
            except Exception as e:
                self.debug_print(f"Error unprotecting tasks: {e}")
        
        return tasks_df

    def identify_stale_tasks(self, df=None, days_threshold=None):
        """
        Identify tasks that need reminders.
        
        Args:
            df: DataFrame containing tasks. If None, fetches tasks.
            days_threshold: Days before a task is considered stale.
                           If None, uses value from config.
                           
        Returns:
            pd.DataFrame: DataFrame containing stale tasks.
        """
        if df is None:
            df = self.fetch_tasks()
        
        if days_threshold is None:
            days_threshold = DAYS_THRESHOLD
            
        now = datetime.now()
        # Handle potential None values in date column
        df["days_old"] = df["date"].apply(lambda d: (now - d).days if d else 0)

        # Basic stale task identification
        stale_tasks = df[(df["status"] != "Completed") & 
                         (df["days_old"] > days_threshold) & 
                         (~df["reminder_sent"])]

        return stale_tasks

    def mark_task_as_reminded(self, task_id):
        """
        Mark a task as reminded in Notion.
        
        Args:
            task_id: ID of the task to mark as reminded.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            self.client.pages.update(
                page_id=task_id,
                properties={"Reminder Sent": {"checkbox": True}}
            )
            return True
        except Exception as e:
            self.debug_print(f"Error marking task as reminded: {e}")
            return False

    def insert_task(self, task):
        """
        Insert a new task into Notion.
        
        Args:
            task: Dictionary containing task information.
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Make sure date is in the right format for Notion
            date_str = task["date"]
            if isinstance(date_str, datetime):
                date_str = date_str.strftime("%Y-%m-%d")

            # Create the task in Notion
            self.client.pages.create(
                parent={"database_id": self.task_db_id},
                properties={
                    "Task": {
                        "title": [{"text": {"content": task["task"]}}]
                    },
                    "Status": {
                        "select": {"name": task["status"]}
                    },
                    "Date": {
                        "date": {"start": date_str}
                    },
                    "Employee": {
                        "rich_text": [{"text": {"content": task["employee"]}}]
                    },
                    "Reminder sent": {
                        "checkbox": False
                    },
                    "Category": {
                        "rich_text": [{"text": {"content": task["category"]}}]
                    }
                }
            )
            return True, f"✅ Added new task: {task['task']}"
        except Exception as e:
            self.debug_print(f"Task creation error details: {traceback.format_exc()}")
            return False, f"❌ Error creating task: {e}"

    def update_task(self, task_id, task):
        """
        Update task with intelligent field updates.
        
        Args:
            task_id: ID of the task to update.
            task: Dictionary containing updated task information.
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Build update properties
            update_props = {
                # Always update status
                "Status": {"select": {"name": task["status"]}}
            }

            # Only update other fields if they provide more information
            # For example, we could update the description if the new one is more detailed

            # Update the task
            self.client.pages.update(
                page_id=task_id,
                properties=update_props
            )
            return True, f"✅ Updated task: {task['task']}"
        except Exception as e:
            self.debug_print(f"Task update error details: {traceback.format_exc()}")
            return False, f"❌ Error updating task: {e}"

    def fetch_peer_feedback(self, person_name, days_back=14):
        """
        Fetch peer feedback for a specific person.
        
        Args:
            person_name: Name of the person to fetch feedback for.
            days_back: Number of days back to fetch feedback for.
            
        Returns:
            list: List of feedback dictionaries.
        """
        if not person_name or not self.feedback_db_id:
            return []

        recent_cutoff = datetime.now() - timedelta(days=days_back)

        try:
            all_results = []
            has_more = True
            start_cursor = None

            while has_more:
                response = self.client.databases.query(
                    database_id=self.feedback_db_id,
                    start_cursor=start_cursor,
                    page_size=100
                )

                all_results.extend(response["results"])
                has_more = response["has_more"]

                if has_more:
                    start_cursor = response["next_cursor"]

            entries = []
            for row in all_results:
                try:
                    props = row["properties"]
                    name = self.get_title_content(props, "Name")
                    feedback = self.get_rich_text_content(props, "Feedback")
                    date = self.get_date_value(props, "Date")

                    if name.lower() == person_name.lower() and date and date >= recent_cutoff:
                        entries.append({"date": date.strftime("%Y-%m-%d"), "feedback": feedback})
                except Exception as e:
                    self.debug_print(f"Error processing feedback entry: {e}")
                    continue

            return entries
        except Exception as e:
            self.debug_print(f"Error fetching peer feedback: {e}")
            return []

    def list_all_categories(self):
        """
        Get all unique categories from existing tasks.
        
        Returns:
            list: List of category names.
        """
        try:
            df = self.fetch_tasks()
            categories = sorted(df["category"].dropna().unique().tolist())
            # Add "Uncategorized" if it doesn't exist
            if not categories:
                categories = ["Uncategorized"]
            return categories
        except Exception as e:
            self.debug_print(f"Error listing categories: {e}")
            return ["Uncategorized"]  # Fallback