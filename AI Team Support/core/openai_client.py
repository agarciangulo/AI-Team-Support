"""
OpenAI API integration for Task Manager.
Handles embeddings and AI-generated insights.
"""
import json
import os
import traceback
from hashlib import md5
import numpy as np
from openai import OpenAI

from config import (
    OPENAI_API_KEY, 
    EMBEDDING_CACHE_PATH, 
    EMBEDDING_MODEL, 
    CHAT_MODEL, 
    DEBUG_MODE,
    MIN_TASK_LENGTH
)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize embedding cache
embedding_cache = {}
embedding_cache_path = EMBEDDING_CACHE_PATH

# Load embedding cache if exists
if os.path.exists(embedding_cache_path):
    try:
        with open(embedding_cache_path, "r") as f:
            embedding_cache = json.load(f)
        print(f"✅ Loaded {len(embedding_cache)} embeddings from cache")
    except json.JSONDecodeError:
        print("❌ Embedding cache file corrupted, starting with empty cache")
        embedding_cache = {}

def debug_print(message):
    """Print debug messages if DEBUG_MODE is True."""
    if DEBUG_MODE:
        print(message)

def get_cached_embedding(text):
    """Get embedding for a single text, using cache if available."""
    if not text or not isinstance(text, str) or len(text.strip()) < MIN_TASK_LENGTH:
        return None

    text_hash = md5(text.encode()).hexdigest()
    if text_hash in embedding_cache:
        return embedding_cache[text_hash]

    try:
        response = client.embeddings.create(
            input=[text],
            model=EMBEDDING_MODEL
        )
        embedding = response.data[0].embedding
        embedding_cache[text_hash] = embedding

        # Save cache periodically to avoid losing data
        with open(embedding_cache_path, "w") as f:
            json.dump(embedding_cache, f)

        return embedding
    except Exception as e:
        debug_print(f"Error getting embedding: {e}")
        return None

def get_batch_embeddings(texts):
    """Get embeddings for multiple texts, using cache where possible."""
    if not texts:
        return {}

    # Filter out invalid texts
    valid_texts = [t for t in texts if isinstance(t, str) and len(t.strip()) >= MIN_TASK_LENGTH]
    if not valid_texts:
        return {}

    hash_lookup = {md5(t.encode()).hexdigest(): t for t in valid_texts}
    embeddings = {}
    texts_to_request = []

    # Check cache first
    for h, t in hash_lookup.items():
        if h in embedding_cache:
            embeddings[h] = embedding_cache[h]
        else:
            texts_to_request.append(t)

    # Only call API if we have texts not in cache
    if texts_to_request:
        try:
            # Split into batches to avoid exceeding API limits
            batch_size = 100  # Adjust based on API limits
            for i in range(0, len(texts_to_request), batch_size):
                batch = texts_to_request[i:i+batch_size]

                response = client.embeddings.create(
                    input=batch,
                    model=EMBEDDING_MODEL
                )

                for i, t in enumerate(batch):
                    h = md5(t.encode()).hexdigest()
                    embedding_cache[h] = response.data[i].embedding
                    embeddings[h] = response.data[i].embedding

            # Save the updated cache
            with open(embedding_cache_path, "w") as f:
                json.dump(embedding_cache, f)
        except Exception as e:
            debug_print(f"Error in batch embeddings: {e}")

    # Return embeddings mapped to original texts
    return {hash_lookup[h]: embeddings[h] for h in embeddings}

def get_coaching_insight(person_name, tasks, recent_tasks, peer_feedback):
    """Generate coaching insights using OpenAI."""
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

    feedback_prompt = f"""
    You are CoachAI, a friendly and helpful workplace assistant who offers coaching insights in a conversational, supportive tone.

    ANALYZE THE FOLLOWING DATA FOR {person_name}:
    1. Current tasks: {tasks}
    2. Task history (14 days): {recent_tasks[['task', 'status', 'employee', 'date', 'category']].to_dict(orient='records') if not recent_tasks.empty else []}
    3. Basic statistics: {basic_stats}
    4. Peer feedback: {peer_feedback}

    FIRST, ANALYZE THIS DATA TO IDENTIFY PATTERNS:
    - Task completion rates and patterns
    - Work distribution across different projects
    - Recent productivity trends
    - Task complexity and priority handling
    - Collaboration patterns

    THEN, PROVIDE INSIGHTS ON THE ANALYSIS IN A CONVERSATIONAL TONE, INCLUDING:
    1. A specific strength or accomplishment to recognize
    2. Spefic instances that require their immediate attention
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
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": feedback_prompt}],
            temperature=0.4
        )
        reflection = response.choices[0].message.content
        return reflection
    except Exception as e:
        debug_print(f"Error generating coaching insights: {e}")
        return "Unable to generate coaching insights at this time."

def get_project_insight(selected_category, filtered_tasks):
    """Generate project insights using OpenAI."""
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

    # AI-generated insight based on tasks in the category
    project_prompt = f"""
    You are ProjectAnalyst, a strategic advisor on project management and team productivity.

    ANALYZE PROJECT '{selected_category}' TASKS:
    {filtered_tasks[['task', 'status', 'employee', 'date']].to_dict(orient='records')}

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
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": project_prompt}],
            temperature=0.5
        )
        insight = response.choices[0].message.content
        return insight.strip()
    except Exception as e:
        debug_print(f"Error generating project insight: {e}")
        return f"⚠️ Unable to generate AI insight: {e}"