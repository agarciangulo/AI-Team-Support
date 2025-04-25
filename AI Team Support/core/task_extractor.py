"""
Task extraction functionality for Task Manager.
Handles extracting structured tasks from freeform text.
"""
import json
import re
import ast
import traceback
from dateutil import parser
from datetime import datetime
from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    MIN_TASK_LENGTH, 
    DEBUG_MODE,
    CHAT_MODEL
)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def debug_print(message):
    """Print debug messages if DEBUG_MODE is True."""
    if DEBUG_MODE:
        print(message)

def extract_tasks_from_update(text):
    """Extract structured tasks from freeform text with improved error handling."""
    if not text or len(text.strip()) < MIN_TASK_LENGTH:
        return []

    print("Starting task extraction...")

    prompt = f"""You are TaskExtractor, an expert system that extracts structured task updates from complex work logs and emails.

YOUR TASK:
Extract ONLY the actionable tasks from the provided work log, which may contain forwarded emails, email threads, or multiple reports. Follow these precise steps:

1. EMAIL STRUCTURE ANALYSIS:
   - Identify the most recent and relevant activity report in the email thread
   - Recognize different report formats (Hours Breakdown, Planned vs Completed, etc.)
   - Identify the primary author of each section
   - Handle forwarded emails by associating tasks with the correct person

2. SENDER IDENTIFICATION:
   - Extract the full name of the person who performed the tasks (not necessarily the email sender)
   - If multiple people are mentioned, correctly attribute tasks to each person
   - Look for patterns like "From:", email signatures, or introductory lines to identify the task performer

3. TASK EXTRACTION STRATEGIES:
   - Look for explicit "Completed Activities" or "Completed Tasks" sections first
   - Extract from "Planned Activities" only if corresponding completed activities are not found
   - Recognize tasks in bullet points, numbered lists, paragraphs, and project sections
   - Parse tasks across different formatting styles (dashes, asterisks, paragraphs)
   - Identify action verbs to determine what work was performed
   - Ignore email headers, greetings, and signatures that don't contain task information

4. STATUS DETERMINATION - CLASSIFY AS:
   - "Completed": Task explicitly marked as completed or described in past tense
   - "In Progress": Work started but explicitly mentioned as not finished
   - "Pending": Mentioned in "Planned" section but not in "Completed" section
   - "Blocked": Explicitly mentioned as blocked by dependencies or issues

5. DATE EXTRACTION:
   - For each task, extract the date when it was performed
   - If not explicitly mentioned with the task, use the email date
   - Standardize all dates to YYYY-MM-DD format
   - For emails with multiple dates, use the most recent relevant date for each task

6. CATEGORIZATION:
   - Assign each task to the correct project/category based on context
   - Use section headers, indentation, or prefix labels to determine categories
   - If a task mentions multiple projects, prefer the most specific one
   - If no category is explicitly mentioned, use "Uncategorized"

7. TASK ENHANCEMENT:
   - Ensure each task has a clear action verb
   - Include sufficient context to understand what was accomplished
   - Connect related information to create coherent task descriptions
   - Preserve technical terms, project names, and specific references

IMPORTANT OUTPUT REQUIREMENTS:
- Return ONLY a valid Python list of dictionaries with EXACTLY these keys: "task", "status", "employee", "date", "category"
- Each task description must be clear, specific, and self-contained
- Date format must be YYYY-MM-DD
- Status must be exactly one of: "Completed", "In Progress", "Pending", "Blocked"
- Do not include explanations, markdown, or any text outside the list of task dictionaries

SPECIAL CASES TO HANDLE:
- Handle tasks mentioned in both "Planned" and "Completed" sections by creating only one task entry
- For "Hours Breakdown" sections, extract the categories but don't treat the hours as tasks
- Ignore tasks that are merely attendance at meetings unless specific contributions are mentioned
- When a task spans multiple emails or days, extract it only once with the most recent status

Now extract the tasks from this input: {text}"""

    try:
        print("Calling OpenAI API...")
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response.choices[0].message.content
        print(f"Received response from OpenAI. Length: {len(content)}")

        # Remove markdown code blocks if present
        if "```" in content:
            print("Removing markdown code blocks...")
            content = re.sub(r'```(?:python|json)?\n(.*?)```', r'\1', content, flags=re.DOTALL)

        content = content.strip()
        print(f"Cleaned content. Now parsing...")

        # Try multiple parsing methods in sequence
        tasks = None

        # Method 1: Direct JSON parsing
        try:
            print("Attempting direct JSON parsing...")
            # Replace single quotes with double quotes for JSON
            json_content = content.replace("'", '"')
            tasks = json.loads(json_content)
            print("JSON parsing successful!")
        except json.JSONDecodeError as e:
            print(f"JSON parse failed: {e}")

            # Method 2: Extract array with regex
            try:
                print("Attempting to extract JSON array with regex...")
                match = re.search(r'\[\s*{.*}\s*\]', content, re.DOTALL)
                if match:
                    json_array = match.group(0).replace("'", '"')
                    tasks = json.loads(json_array)
                    print("Regex extraction successful!")
                else:
                    print("No JSON array found in content")
            except Exception as e:
                print(f"Regex extraction failed: {e}")

                # Method 3: Fall back to safer eval
                try:
                    print("Attempting eval with ast...")
                    tasks = ast.literal_eval(content)
                    print("AST literal_eval successful!")
                except Exception as e:
                    print(f"AST literal_eval failed: {e}")

                    # Final fallback: Try eval directly
                    try:
                        print("Last resort: direct eval...")
                        tasks = eval(content)
                        print("Direct eval successful!")
                    except Exception as e:
                        print(f"All parsing methods failed: {e}")
                        raise ValueError("Could not parse AI response as valid task data")

        # Ensure tasks is a list of dictionaries
        if not isinstance(tasks, list):
            print(f"Parsed result is not a list: {type(tasks)}")
            raise ValueError(f"Expected a list of tasks, got {type(tasks)}")

        # Type checking for each task
        valid_tasks = []
        for i, task in enumerate(tasks):
            try:
                if not isinstance(task, dict):
                    print(f"Task {i} is not a dictionary: {type(task)}")
                    continue

                # Ensure all required keys exist
                required_keys = ["task", "status", "employee", "date", "category"]
                if not all(key in task for key in required_keys):
                    missing = [key for key in required_keys if key not in task]
                    print(f"Task {i} missing keys: {missing}")
                    continue

                # Ensure task description has minimum length
                if not task["task"] or len(task["task"].strip()) < MIN_TASK_LENGTH:
                    print(f"Task {i} description too short: '{task['task']}'")
                    continue

                # Standardize date format
                if isinstance(task["date"], str):
                    try:
                        date_obj = parser.parse(task["date"])
                        task["date"] = date_obj.strftime("%Y-%m-%d")
                    except Exception as e:
                        print(f"Date parsing error for task {i}: {e}")
                        # Default to today's date if parsing fails
                        task["date"] = datetime.now().strftime("%Y-%m-%d")

                valid_tasks.append(task)
            except Exception as e:
                print(f"Error validating task {i}: {e}")
                continue

        print(f"Successfully validated {len(valid_tasks)} tasks")
        return valid_tasks

    except Exception as e:
        import traceback
        print(f"Error extracting tasks: {e}")
        print(traceback.format_exc())
        # Return a more informative error that you'll display to the user
        raise ValueError(f"Task extraction failed: {str(e)}")

        print("Calling OpenAI API...")
        response = openai.ChatCompletion.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response["choices"][0]["message"]["content"]
        print(f"Received response from OpenAI. Length: {len(content)}")

        # Remove markdown code blocks if present
        if "```" in content:
            print("Removing markdown code blocks...")
            content = re.sub(r'```(?:python|json)?\n(.*?)```', r'\1', content, flags=re.DOTALL)

        content = content.strip()
        print(f"Cleaned content. Now parsing...")

        # Try multiple parsing methods in sequence
        tasks = None

        # Method 1: Direct JSON parsing
        try:
            print("Attempting direct JSON parsing...")
            # Replace single quotes with double quotes for JSON
            json_content = content.replace("'", '"')
            tasks = json.loads(json_content)
            print("JSON parsing successful!")
        except json.JSONDecodeError as e:
            print(f"JSON parse failed: {e}")

            # Method 2: Extract array with regex
            try:
                print("Attempting to extract JSON array with regex...")
                match = re.search(r'\[\s*{.*}\s*\]', content, re.DOTALL)
                if match:
                    json_array = match.group(0).replace("'", '"')
                    tasks = json.loads(json_array)
                    print("Regex extraction successful!")
                else:
                    print("No JSON array found in content")
            except Exception as e:
                print(f"Regex extraction failed: {e}")

                # Method 3: Fall back to safer eval
                try:
                    print("Attempting eval with ast...")
                    tasks = ast.literal_eval(content)
                    print("AST literal_eval successful!")
                except Exception as e:
                    print(f"AST literal_eval failed: {e}")

                    # Final fallback: Try eval directly
                    try:
                        print("Last resort: direct eval...")
                        tasks = eval(content)
                        print("Direct eval successful!")
                    except Exception as e:
                        print(f"All parsing methods failed: {e}")
                        raise ValueError("Could not parse AI response as valid task data")

        # Ensure tasks is a list of dictionaries
        if not isinstance(tasks, list):
            print(f"Parsed result is not a list: {type(tasks)}")
            raise ValueError(f"Expected a list of tasks, got {type(tasks)}")

        # Type checking for each task
        valid_tasks = []
        for i, task in enumerate(tasks):
            try:
                if not isinstance(task, dict):
                    print(f"Task {i} is not a dictionary: {type(task)}")
                    continue

                # Ensure all required keys exist
                required_keys = ["task", "status", "employee", "date", "category"]
                if not all(key in task for key in required_keys):
                    missing = [key for key in required_keys if key not in task]
                    print(f"Task {i} missing keys: {missing}")
                    continue

                # Ensure task description has minimum length
                if not task["task"] or len(task["task"].strip()) < MIN_TASK_LENGTH:
                    print(f"Task {i} description too short: '{task['task']}'")
                    continue

                # Standardize date format
                if isinstance(task["date"], str):
                    try:
                        date_obj = parser.parse(task["date"])
                        task["date"] = date_obj.strftime("%Y-%m-%d")
                    except Exception as e:
                        print(f"Date parsing error for task {i}: {e}")
                        # Default to today's date if parsing fails
                        task["date"] = datetime.now().strftime("%Y-%m-%d")

                valid_tasks.append(task)
            except Exception as e:
                print(f"Error validating task {i}: {e}")
                continue

        print(f"Successfully validated {len(valid_tasks)} tasks")
        return valid_tasks

    except Exception as e:
        import traceback
        print(f"Error extracting tasks: {e}")
        print(traceback.format_exc())
        # Return a more informative error that you'll display to the user
        raise ValueError(f"Task extraction failed: {str(e)}")