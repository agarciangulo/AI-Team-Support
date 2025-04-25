"""
Configuration settings for the Task Manager application.
"""
import os

# API Keys - Use environment variables for better security
OPENAI_API_KEY = "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"
NOTION_TOKEN = "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"

# Database IDs
NOTION_DATABASE_ID = "1a35c6ec3b80801fb280d632be392e46"
NOTION_FEEDBACK_DB_ID = "1cc5c6ec3b8080ab934feb388e729447"

# Configuration settings
SIMILARITY_THRESHOLD = 0.85  # Threshold for task similarity
ENABLE_TASK_VALIDATION = True  # Set to False to bypass validation
MIN_TASK_LENGTH = 5  # Minimum length for a valid task
DAYS_THRESHOLD = 2  # Days before a task is considered stale
DEBUG_MODE = True  # Enable debug prints

# File paths
EMBEDDING_CACHE_PATH = "embedding_cache.json"

# OpenAI model configuration
EMBEDDING_MODEL = "text-embedding-ada-002"
CHAT_MODEL = "gpt-4"