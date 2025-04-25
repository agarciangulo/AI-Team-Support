"""
Core package for Task Manager.
This module provides compatibility with the old structure.
"""
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
