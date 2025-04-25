"""
Task processing functionality for Task Manager.
Handles task similarity matching and processing for Notion integration.
"""
import numpy as np
import traceback
from datetime import datetime, timedelta
from sklearn.metrics.pairwise import cosine_similarity

from config import (
    DEBUG_MODE, 
    SIMILARITY_THRESHOLD, 
    MIN_TASK_LENGTH
)
from core.openai_client import get_batch_embeddings
from core.notion_client import insert_task_to_notion, update_task_in_notion
from plugins import plugin_manager

def debug_print(message):
    """Print debug messages if DEBUG_MODE is True."""
    if DEBUG_MODE:
        print(message)

def classify_task_type(task):
    """Classify task into different types for specialized handling."""
    task_lower = task["task"].lower()

    # Training/class pattern
    if any(keyword in task_lower for keyword in ["class", "training", "certification", "learning"]):
        return "training"

    # Meeting/attendance pattern
    if any(keyword in task_lower for keyword in ["attended", "meeting", "call", "sync", "session"]):
        return "meeting"

    # Recurring task pattern
    if any(keyword in task_lower for keyword in ["weekly", "daily", "monthly", "recurring"]):
        return "recurring"

    # Admin task pattern
    if task["category"].lower() == "admin":
        return "admin"

    # Default: regular task
    return "regular"

def insert_or_update_task(task, existing_tasks, log_output=None):
    """Insert a new task or update existing similar task with intelligent matching."""
    # Initialize log_output if not provided
    if log_output is None:
        log_output = []
        
    # Don't process empty tasks
    if not task["task"] or len(task["task"].strip()) < MIN_TASK_LENGTH:
        log_output.append(f"⚠️ Skipping empty or too short task")
        return

    try:
        log_output.append(f"📋 Processing task: '{task['task']}'")
        
        # Get the project protection plugin if available
        protection_plugin = plugin_manager.get_plugin('ProjectProtectionPlugin')
        use_protection = protection_plugin and protection_plugin.enabled

        # Protect task data before processing if needed
        protected_task = task
        if use_protection:
            try:
                protected_task = protection_plugin.protect_task(task)
            except Exception as e:
                log_output.append(f"⚠️ Error protecting task data: {e}")
                # Continue with unprotected data

        # Determine if this is a recurring task
        is_recurring = classify_task_type(task) in ["training", "meeting", "recurring"]

        # For recurring tasks, we need exact matching with date
        if is_recurring:
            # Convert task date to string for comparison if it's a datetime
            task_date = task["date"]
            if isinstance(task_date, datetime):
                task_date = task_date.strftime("%Y-%m-%d")

            # Find tasks with same description and date
            matching_tasks = existing_tasks[
                (existing_tasks["task"] == task["task"]) &
                (existing_tasks["employee"] == task["employee"])
            ]

            # Check if any matching task has the same date (allowing string/datetime comparison)
            for _, row in matching_tasks.iterrows():
                row_date = row["date"]
                if isinstance(row_date, datetime):
                    row_date = row_date.strftime("%Y-%m-%d")

                if task_date == row_date:
                    log_output.append(f"🔁 Updating recurring task with exact match: {row['task']} → {task['status']}")
                    
                    # Use the protected task for update if protection is enabled
                    task_to_update = protected_task if use_protection else task
                    success, message = update_task_in_notion(row["id"], task_to_update)
                    log_output.append(message)
                    return

        # For regular tasks or if no exact match was found for recurring tasks
        # Get embeddings for task
        task_embeddings = get_batch_embeddings([task["task"]])
        if not task_embeddings or task["task"] not in task_embeddings:
            log_output.append(f"⚠️ Could not generate embedding for task: '{task['task']}'")
            # Insert as new task since we can't compare
            
            # Use the protected task for insertion if protection is enabled
            task_to_insert = protected_task if use_protection else task
            success, message = insert_task_to_notion(task_to_insert)
            log_output.append(message)
            return

        task_embedding = task_embeddings[task["task"]]

        # Get embeddings for existing tasks
        existing_texts = existing_tasks["task"].tolist()
        existing_embeddings = get_batch_embeddings(existing_texts)

        best_score = 0
        best_match = None

        # Find best matching existing task
        for _, row in existing_tasks.iterrows():
            if row["task"] not in existing_embeddings:
                continue

            existing_embedding = np.array(existing_embeddings[row["task"]])

            # Basic similarity calculation
            similarity = cosine_similarity([task_embedding], [existing_embedding])[0][0]

            # Adjust similarity based on metadata
            # If same employee, increase similarity
            if task["employee"] == row["employee"]:
                similarity += 0.05

            # If same category, increase similarity
            if task["category"] == row["category"]:
                similarity += 0.05

            # If different dates, decrease similarity for recurring tasks
            if is_recurring:
                task_date = task["date"] if isinstance(task["date"], str) else task["date"].strftime("%Y-%m-%d") if task["date"] else None
                row_date = row["date"] if isinstance(row["date"], str) else row["date"].strftime("%Y-%m-%d") if row["date"] else None

                if task_date != row_date:
                    similarity -= 0.1

            if similarity > best_score:
                best_score = similarity
                best_match = row

        log_output.append(f"🎯 Best match score: {best_score:.2f} for task: '{task['task']}'\n")

        # Determine threshold based on task type
        threshold = SIMILARITY_THRESHOLD
        if is_recurring:
            threshold = 0.9  # Higher threshold for recurring tasks

        # Update existing task if similarity is above threshold
        if best_score > threshold:
            log_output.append(f"🔁 Updating existing task: {best_match['task']} → {task['status']}")
            try:
                # Use the protected task for update if protection is enabled
                task_to_update = protected_task if use_protection else task
                success, message = update_task_in_notion(best_match["id"], task_to_update)
                log_output.append(message)
            except Exception as e:
                log_output.append(f"❌ Error updating task: {e}")
        else:
            # Insert as new task
            # Use the protected task for insertion if protection is enabled
            task_to_insert = protected_task if use_protection else task
            success, message = insert_task_to_notion(task_to_insert)
            log_output.append(message)
    except Exception as e:
        log_output.append(f"❌ Error in task processing: {e}")
        debug_print(f"Task processing error details: {traceback.format_exc()}")