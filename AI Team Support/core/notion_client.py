"""
Notion API integration for Task Manager.
Handles all interactions with Notion databases.
"""
from notion_client import Client
from datetime import datetime, timedelta
from dateutil import parser
import pandas as pd
import traceback

from config import (
    NOTION_TOKEN, 
    NOTION_DATABASE_ID, 
    NOTION_FEEDBACK_DB_ID, 
    DEBUG_MODE, 
    DAYS_THRESHOLD
)

# Initialize Notion client
notion = Client(auth=NOTION_TOKEN)
database_id = NOTION_DATABASE_ID
feedback_db_id = NOTION_FEEDBACK_DB_ID

def debug_print(message):
    """Print debug messages if DEBUG_MODE is True."""
    if DEBUG_MODE:
        print(message)

def validate_notion_connection():
    """Validate connection to Notion API."""
    try:
        response = notion.databases.query(database_id=database_id, page_size=1)
        print("✅ Notion connection successful!")
        return True
    except Exception as e:
        print(f"❌ Notion connection failed: {e}")
        return False

# Helper functions for safer Notion property access
def get_title_content(props, key):
    """Safely extract title content from Notion properties."""
    try:
        if key in props and props[key]["title"] and len(props[key]["title"]) > 0:
            return props[key]["title"][0]["text"]["content"]
        return ""
    except (KeyError, IndexError):
        return ""

def get_select_value(props, key, default=""):
    """Safely extract select value from Notion properties."""
    try:
        if key in props and props[key].get("select"):
            return props[key]["select"]["name"]
        return default
    except KeyError:
        return default

def get_rich_text_content(props, key):
    """Safely extract rich text content from Notion properties."""
    try:
        if key in props and props[key].get("rich_text") and len(props[key]["rich_text"]) > 0:
            return props[key]["rich_text"][0]["text"]["content"]
        return ""
    except (KeyError, IndexError):
        return ""

def get_date_value(props, key):
    """Safely extract date value from Notion properties."""
    try:
        if key in props and props[key].get("date") and props[key]["date"].get("start"):
            return parser.parse(props[key]["date"]["start"])
        return None
    except (KeyError, ValueError, TypeError):
        return None

def get_checkbox_value(props, key, default=False):
    """Safely extract checkbox value from Notion properties."""
    try:
        if key in props:
            return props[key]["checkbox"]
        return default
    except KeyError:
        return default

def fetch_notion_tasks():
    """Fetch tasks from Notion with pagination support."""
    all_pages = []
    has_more = True
    start_cursor = None

    while has_more:
        response = notion.databases.query(
            database_id=database_id,
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
                "task": get_title_content(props, "Task"),
                "status": get_select_value(props, "Status", "No Status"),
                "employee": get_rich_text_content(props, "Employee"),
                "date": get_date_value(props, "Date"),
                "reminder_sent": get_checkbox_value(props, "Reminder Sent", False),
                "category": get_rich_text_content(props, "Category"),
            }
            rows.append(task)
        except Exception as e:
            debug_print(f"Error processing Notion page {page['id']}: {e}")
            continue

    return pd.DataFrame(rows)

def identify_stale_tasks(df, days_threshold=DAYS_THRESHOLD):
    """Identify tasks that need reminders."""
    now = datetime.now()
    # Handle potential None values in date column
    df["days_old"] = df["date"].apply(lambda d: (now - d).days if d else 0)

    # Basic stale task identification
    stale_tasks = df[(df["status"] != "Completed") & (df["days_old"] > days_threshold) & (~df["reminder_sent"])]

    return stale_tasks

def mark_task_as_reminded(task_id):
    """Mark a task as reminded in Notion."""
    try:
        notion.pages.update(
            page_id=task_id,
            properties={"Reminder Sent": {"checkbox": True}}
        )
        return True
    except Exception as e:
        debug_print(f"Error marking task as reminded: {e}")
        return False

def insert_task_to_notion(task):
    """Insert a new task into Notion."""
    try:
        # Make sure date is in the right format for Notion
        date_str = task["date"]
        if isinstance(date_str, datetime):
            date_str = date_str.strftime("%Y-%m-%d")

        notion.pages.create(
            parent={"database_id": database_id},
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
        debug_print(f"Task creation error details: {traceback.format_exc()}")
        return False, f"❌ Error creating task: {e}"

def update_task_in_notion(task_id, task):
    """Update task with intelligent field updates."""
    try:
        # Build update properties
        update_props = {
            # Always update status
            "Status": {"select": {"name": task["status"]}}
        }

        # Only update other fields if they provide more information
        # For example, we could update the description if the new one is more detailed

        # Update the task
        notion.pages.update(
            page_id=task_id,
            properties=update_props
        )
        return True, f"✅ Updated task: {task['task']}"
    except Exception as e:
        debug_print(f"Task update error details: {traceback.format_exc()}")
        return False, f"❌ Error updating task: {e}"

def fetch_peer_feedback(person_name, days_back=14):
    """Fetch peer feedback for a specific person."""
    if not person_name or not feedback_db_id:
        return []

    recent_cutoff = datetime.now() - timedelta(days=days_back)

    try:
        all_results = []
        has_more = True
        start_cursor = None

        while has_more:
            response = notion.databases.query(
                database_id=feedback_db_id,
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
                name = get_title_content(props, "Name")
                feedback = get_rich_text_content(props, "Feedback")
                date = get_date_value(props, "Date")

                if name.lower() == person_name.lower() and date and date >= recent_cutoff:
                    entries.append({"date": date.strftime("%Y-%m-%d"), "feedback": feedback})
            except Exception as e:
                debug_print(f"Error processing feedback entry: {e}")
                continue

        return entries
    except Exception as e:
        debug_print(f"Error fetching peer feedback: {e}")
        return []

def list_all_categories():
    """Get all unique categories from existing tasks."""
    try:
        df = fetch_notion_tasks()
        categories = sorted(df["category"].dropna().unique().tolist())
        # Add "Uncategorized" if it doesn't exist
        if not categories:
            categories = ["Uncategorized"]
        return categories
    except Exception as e:
        debug_print(f"Error listing categories: {e}")
        return ["Uncategorized"]  # Fallback