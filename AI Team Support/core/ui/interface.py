"""
Gradio UI for Task Manager application.
"""
import gradio as gr
import pandas as pd
from datetime import datetime, timedelta

from config import (
    DEBUG_MODE
)
from core.notion_client import (
    fetch_notion_tasks, 
    identify_stale_tasks, 
    list_all_categories, 
    fetch_peer_feedback
)
from core.openai_client import (
    get_coaching_insight,
    get_project_insight
)
from core.task_extractor import extract_tasks_from_update
from core.task_processor import insert_or_update_task

def process_freeform_input(update_text):
    """Process freeform text input and handle task extraction and validation."""
    try:
        # Clear log output for new processing
        log_output = []
        
        # Show loading message
        log_output.append("⏳ Processing your update...")

        # Extract tasks from update text
        print(f"Extracting tasks from update...")
        tasks = extract_tasks_from_update(update_text)

        if not tasks:
            return "❌ No tasks could be extracted from your update. Please check your input and try again."

        log_output.append(f"✅ Extracted {len(tasks)} tasks from your update")

        # Get existing tasks from Notion
        log_output.append("⏳ Fetching existing tasks from Notion...")
        existing_tasks = fetch_notion_tasks()
        log_output.append(f"✅ Fetched {len(existing_tasks)} existing tasks")

        # Process clear tasks
        log_output.append("⏳ Processing tasks...")
        for task in tasks:
            insert_or_update_task(task, existing_tasks, log_output)

        # Get more info for coaching insights
        person_name = ""
        if tasks:
            if isinstance(tasks[0], dict) and "employee" in tasks[0]:
                person_name = tasks[0].get("employee", "")

        # Only fetch feedback if we have a person name
        peer_feedback = []
        if person_name:
            try:
                peer_feedback = fetch_peer_feedback(person_name)
                log_output.append(f"✅ Fetched {len(peer_feedback)} peer feedback entries")
            except Exception as e:
                log_output.append(f"⚠️ Error fetching peer feedback: {e}")

        # Get recent tasks for coaching insights
        recent_tasks = pd.DataFrame()
        try:
            recent_tasks = existing_tasks[existing_tasks['date'] >= datetime.now() - timedelta(days=14)]
            log_output.append(f"✅ Retrieved {len(recent_tasks)} recent tasks for analysis")
        except Exception as e:
            log_output.append(f"⚠️ Error retrieving recent tasks: {e}")
            print(f"Recent tasks error: {traceback.format_exc()}")

        # Generate coaching insights
        log_output.append("⏳ Generating coaching insights...")
        
        try:
            reflection = get_coaching_insight(person_name, tasks, recent_tasks, peer_feedback)
            log_output.append("✅ Generated coaching insights")
        except Exception as e:
            log_output.append(f"⚠️ Error generating coaching insights: {e}")
            reflection = "Unable to generate coaching insights at this time."

        # Format output for display
        tasks_print = ""
        for task in tasks:
            if isinstance(task, dict) and "task" in task and "status" in task:
                tasks_print += f"\n - {task['task']} ({task['status']})"
            else:
                print(f"Invalid task format for display: {task}")

        feedback_note = f"✅ {len(tasks)} tasks synced to Notion."
        formatted_log = "\n".join(log_output)
        coaching_intro = "Here's my assessment of your recent work:"

        # Keep the technical logs but hide them in a collapsible section
        if DEBUG_MODE:
            tech_details = f"\n\n<details><summary>Technical Details (click to expand)</summary>\n{formatted_log}\n</details>"
        else:
            tech_details = ""

        # Final message with conversational tone
        final_output = f"{tasks_print}\n\n{feedback_note}\n\n{coaching_intro}\n{reflection.strip()}"

        return final_output
    except Exception as e:
        import traceback
        print(f"Error in process_freeform_input: {traceback.format_exc()}")
        return f"❌ Error processing your update: {e}\n\nPlease try again with a more detailed update or contact support."

def show_stale_tasks():
    """Show overdue tasks that need follow-up."""
    try:
        df = fetch_notion_tasks()
        stale = identify_stale_tasks(df)
        if stale.empty:
            return "✅ No overdue tasks!"

        grouped = stale.groupby("employee")
        result_lines = []
        for name, group in grouped:
            result_lines.append(f"👤 {name}:\n")
            for _, row in group.iterrows():
                date_str = row['date'].strftime('%Y-%m-%d') if row['date'] else "No date"
                result_lines.append(f"   • {row['task']} — {row['status']} (since {date_str})\n")
            result_lines.append("")
        return "".join(result_lines)
    except Exception as e:
        print(f"Error in show_stale_tasks: {traceback.format_exc()}")
        return f"❌ Error checking overdue tasks: {e}"

def show_tasks_by_category(selected_category):
    """Show tasks for a specific project category with enhanced AI insights."""
    if not selected_category:
        return "Please select a category first."

    try:
        df = fetch_notion_tasks()
        filtered = df[(df["category"] == selected_category) & (df["status"] != "Completed")]
        if filtered.empty:
            return f"✅ No open tasks in project '{selected_category}'"

        else:
            grouped = filtered.groupby("employee")
            result_lines = []
            for name, group in grouped:
                result_lines.append(f"👤 {name}:")
                for _, row in group.iterrows():
                    date_str = row['date'].strftime('%Y-%m-%d') if row['date'] else "No date"
                    result_lines.append(f"   • {row['task']} — {row['status']} ({date_str})")
                result_lines.append("\n")

            # Add trend summary by status for this category
            status_summary = filtered["status"].value_counts().to_dict()
            result_lines.append(f"📊 Project '{selected_category}' Task Status Summary:")
            for status, count in status_summary.items():
                result_lines.append(f"   - {status}: {count} task(s)")

            # Get AI insights
            try:
                insight = get_project_insight(selected_category, filtered)
                result_lines.append("\n🧠 AI Project Insight:\n")
                result_lines.append(insight)
            except Exception as e:
                result_lines.append(f"\n⚠️ Unable to generate AI insight: {e}")

            return "\n".join(result_lines)
    except Exception as e:
        print(f"Error in show_tasks_by_category: {traceback.format_exc()}")
        return f"❌ Error getting project tasks: {e}"

def create_ui():
    """Create and configure the Gradio UI."""
    # Try to get initial categories, with a fallback
    try:
        initial_categories = list_all_categories()
    except:
        initial_categories = ["Uncategorized"]
        
    # Create Gradio UI
    with gr.Blocks(title="Task Manager", theme=gr.themes.Soft()) as demo:
        gr.Markdown("## 📝 Daily Task Manager")

        with gr.Row():
            with gr.Column():
                update_text = gr.Textbox(
                    lines=10,
                    label="Paste your daily update here",
                    placeholder="Paste your email or daily status update here..."
                )

                # Add loading state elements
                with gr.Row():
                    submit_btn = gr.Button("Submit Update", variant="primary")
                    loading_indicator = gr.HTML(
                        "<div style='text-align:center; color:#888;'>⏳ Processing...</div>",
                        visible=False
                    )

            with gr.Column():
                result = gr.Textbox(
                    label="Result",
                    lines=15,
                    show_copy_button=True
                )

        with gr.Accordion("Task Management Tools", open=False):
            with gr.Row():
                with gr.Column():
                    reminder_output = gr.Textbox(label="Tasks that need follow-up", lines=10)
                    reminder_btn = gr.Button("🔍 Check Overdue Tasks")

                with gr.Column():
                    category_dropdown = gr.Dropdown(
                        choices=initial_categories,
                        label="Select a Project (Category)",
                        value=initial_categories[0] if initial_categories else None
                    )
                    category_result = gr.Textbox(label="Open Tasks for Project", lines=10)
                    category_btn = gr.Button("🔎 View Tasks by Project")

        with gr.Accordion("Help", open=False):
            gr.Markdown("""
            ### 📋 How to Use

            **Daily Updates**: Paste your email or status report into the text area and click "Submit Update".
            The system will extract tasks, match them with existing tasks, and update Notion.

            **Overdue Tasks**: Click "Check Overdue Tasks" to see tasks pending for more than 2 days.

            **Project View**: Select a project category and click "View Tasks by Project" to see all tasks for that project.

            ### 📝 Format Tips

            For best results, include:

            1. Your name/email at the beginning
            2. Date information
            3. Project or category headers
            4. Clear descriptions of completed and pending work

            Example:
            ```
            John Smith
            April 12, 2025

            Project Alpha:
            - Completed the design documentation
            - Started working on the prototype, will finish by Friday
            - Need to schedule a review meeting with the team

            Project Beta:
            - Waiting for feedback on requirements
            ```
            """)

        # Set up UI events with loading states
        submit_btn.click(
            # First update loading indicator
            fn=lambda: (gr.update(visible=False), gr.update(visible=True)),
            inputs=[],
            outputs=[submit_btn, loading_indicator]
        ).then(
            # Then process the input
            fn=process_freeform_input,
            inputs=[update_text],
            outputs=[result]
        ).then(
            # Finally restore the button
            fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
            inputs=[],
            outputs=[submit_btn, loading_indicator]
        )

        # Add category refresh to update dropdown after task changes
        submit_btn.click(
            fn=lambda: gr.update(choices=list_all_categories()),
            inputs=[],
            outputs=[category_dropdown]
        )

        # Set up other button events
        reminder_btn.click(fn=show_stale_tasks, inputs=[], outputs=[reminder_output])
        category_btn.click(fn=show_tasks_by_category, inputs=[category_dropdown], outputs=[category_result])

    return demo