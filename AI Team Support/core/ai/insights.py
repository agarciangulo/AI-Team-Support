"""
AI-powered insights for Task Manager.
Handles coaching and project insights with security protection.
"""
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from datetime import datetime, timedelta
from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    CHAT_MODEL,
    DEBUG_MODE
)

# Import security plugin for protecting sensitive data
from plugins import plugin_manager

def debug_print(message):
    """Print debug messages if DEBUG_MODE is True."""
    if DEBUG_MODE:
        print(message)

def get_coaching_insight(person_name: str, tasks: List[Dict[str, Any]], recent_tasks: pd.DataFrame, peer_feedback: List[Dict[str, Any]]) -> str:
    """
    Generate coaching insights with security protection for project names.
    
    Args:
        person_name: Name of the person to analyze.
        tasks: Current tasks.
        recent_tasks: Recent task history.
        peer_feedback: Peer feedback entries.
        
    Returns:
        str: Coaching insights.
    """
    # Get the project protection plugin if available
    protection_plugin = plugin_manager.get_plugin('ProjectProtectionPlugin')
    use_protection = protection_plugin and protection_plugin.enabled
    
    # Calculate basic statistics for the AI
    basic_stats = {}
    try:
        if not recent_tasks.empty:
            completed_tasks = recent_tasks[recent_tasks['status'] == 'Completed']
            basic_stats = {
                "total_tasks": len(recent_tasks),
                "completed_tasks": len(completed_tasks),
                "completion_rate": f"{len(completed_tasks) / len(recent_tasks):.1%}" if len(recent_tasks) > 0 else "0%",
                "category_counts": recent_tasks['category'].value_counts().to_dict(),
                "date_range": (recent_tasks['date'].max() - recent_tasks['date'].min()).days + 1 if not recent_tasks.empty else 0
            }
    except Exception as e:
        debug_print(f"Error calculating statistics: {e}")
        basic_stats = {"error": str(e)}
    
    # Protect sensitive information if needed
    protected_tasks = tasks
    protected_stats = basic_stats
    protected_feedback = peer_feedback
    
    if use_protection:
        try:
            # Protect tasks
            protected_tasks = protection_plugin.protect_task_list(tasks)
            
            # Protect category counts in stats
            if "category_counts" in protected_stats:
                protected_counts = {}
                for category, count in protected_stats["category_counts"].items():
                    protected_category = protection_plugin.security_manager.tokenize_project(category)
                    protected_counts[protected_category] = count
                protected_stats["category_counts"] = protected_counts
            
            # Feedback doesn't need protection as it doesn't contain project names
        except Exception as e:
            debug_print(f"Error protecting data: {e}")
            # Continue with unprotected data if protection fails

    feedback_prompt = f"""
    You are CoachAI, a friendly and helpful workplace assistant who offers coaching insights in a conversational, supportive tone.

    ANALYZE THE FOLLOWING DATA FOR {person_name}:
    1. Current tasks: {protected_tasks}
    2. Task history (14 days): {recent_tasks[['task', 'status', 'employee', 'date', 'category']].to_dict(orient='records') if not recent_tasks.empty else []}
    3. Basic statistics: {protected_stats}
    4. Peer feedback: {protected_feedback}

    FIRST, ANALYZE THIS DATA TO IDENTIFY PATTERNS:
    - Task completion rates and patterns
    - Work distribution across different projects
    - Recent productivity trends
    - Task complexity and priority handling
    - Collaboration patterns

    THEN, PROVIDE INSIGHTS ON THE ANALYSIS IN A CONVERSATIONAL TONE, INCLUDING:
    1. A specific strength or accomplishment to recognize
    2. Specific instances that require their immediate attention
    3. A friendly, practical, and tactical suggestion that could help them improve

    IMPORTANT STYLE GUIDANCE:
    - Write as a helpful colleague, not a formal report
    - Use personal language ("I notice...", "You're doing well at...")
    - Keep it brief and conversational (3-4 sentences per insight)
    - Avoid technical terms like "metadata analysis" or "velocity metrics"
    - Don't list categories like "STRENGTH:" or "OPPORTUNITY:" - just flow naturally
    - Sound encouraging and supportive throughout
    """

    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": feedback_prompt}],
            temperature=0.4
        )
        
        insights = response.choices[0].message.content
        
        # Unprotect any project tokens in the insights if needed
        if use_protection:
            try:
                insights = protection_plugin.unprotect_text(insights)
            except Exception as e:
                debug_print(f"Error unprotecting insights: {e}")
                
        return insights
    except Exception as e:
        debug_print(f"Error generating coaching insights: {e}")
        return "Unable to generate coaching insights at this time."

def get_project_insight(selected_category: str, filtered_tasks: pd.DataFrame) -> str:
    """
    Generate project insights with security protection for project names.
    
    Args:
        selected_category: Category/project to analyze.
        filtered_tasks: Tasks filtered for this category.
        
    Returns:
        str: Project insights.
    """
    # Get the project protection plugin if available
    protection_plugin = plugin_manager.get_plugin('ProjectProtectionPlugin')
    use_protection = protection_plugin and protection_plugin.enabled
    
    # Calculate basic statistics for the AI
    basic_stats = {}
    try:
        if not filtered_tasks.empty:
            # Calculate date range
            if 'date' in filtered_tasks.columns and not filtered_tasks['date'].isna().all():
                date_range = (filtered_tasks['date'].max() - filtered_tasks['date'].min()).days + 1
            else:
                date_range = 0

            # Calculate team distribution
            team_counts = filtered_tasks['employee'].value_counts().to_dict()

            basic_stats = {
                "total_tasks": len(filtered_tasks),
                "status_counts": filtered_tasks['status'].value_counts().to_dict(),
                "team_distribution": team_counts,
                "date_range": date_range
            }
    except Exception as e:
        debug_print(f"Error calculating project stats: {e}")
        basic_stats = {"error": str(e)}
    
    # Protect sensitive information if needed
    protected_category = selected_category
    protected_tasks = filtered_tasks
    
    if use_protection:
        try:
            # Protect the category name
            protected_category = protection_plugin.security_manager.tokenize_project(selected_category)
            
            # Convert DataFrame to list of dicts for protection
            tasks_list = []
            for _, row in filtered_tasks.iterrows():
                task_dict = row.to_dict()
                # Ensure 'task' key exists for compatibility with protect_task_data
                if 'task' not in task_dict and 'Task' in task_dict:
                    task_dict['task'] = task_dict['Task']
                tasks_list.append(task_dict)
            
            # Protect each task
            protected_tasks_list = protection_plugin.protect_task_list(tasks_list)
            
            # Convert back to DataFrame if needed
            # For simplicity, we'll just use the list for the prompt
        except Exception as e:
            debug_print(f"Error protecting project data: {e}")
            # Continue with unprotected data if protection fails
            protected_tasks_list = tasks_list

    # AI-generated insight based on tasks in the category
    project_prompt = f"""
    You are ProjectAnalyst, a strategic advisor on project management and team productivity.

    ANALYZE PROJECT '{protected_category}' TASKS:
    {protected_tasks_list if use_protection else filtered_tasks[['task', 'status', 'employee', 'date']].to_dict(orient='records')}

    PROJECT METADATA:
    {basic_stats}

    FIRST, PERFORM A METADATA ANALYSIS ON THE PROJECT:
    - Calculate key project metrics: completion rate, velocity, team distribution
    - Identify how many tasks have been open for more than 7 days
    - Analyze distribution of task ages
    - Determine if certain team members have disproportionate workloads
    - Identify any bottlenecks or common blockers
    - Determine if task completion is on pace with creation

    THEN, PROVIDE A THREE-PART INSIGHT:
    1. HEALTH STATUS: One sentence on overall project health
    2. KEY RISK: The most critical item requiring attention
    3. STRATEGIC RECOMMENDATION: One specific action to improve project health

    Keep your response focused, data-driven, and immediately actionable.
    """

    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": project_prompt}],
            temperature=0.5
        )
        
        insights = response.choices[0].message.content
        
        # Unprotect any project tokens in the insights if needed
        if use_protection:
            try:
                insights = protection_plugin.unprotect_text(insights)
            except Exception as e:
                debug_print(f"Error unprotecting project insights: {e}")
        
        return insights.strip()
    except Exception as e:
        debug_print(f"Error generating project insight: {e}")
        return f"⚠️ Unable to generate AI insight: {e}"