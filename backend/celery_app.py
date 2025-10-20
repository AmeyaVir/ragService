#!/usr/bin/env python3
from celery import Celery
# CORRECTED: Use relative import for config
from .config import get_settings 

# Load settings to get the Redis URL
settings = get_settings()

# Initialize the Celery application
# This is placed here to avoid circular dependencies with main.py
celery_app = Celery(
    "analytics_rag",
    broker=settings.redis_url,
    backend=settings.redis_url,
    # CRITICAL FIX: Changed task module path to absolute path relative to the top-level package.
    # Celery will now look for 'backend.tasks.document_tasks'.
    include=['backend.tasks.document_tasks'] 
)

# Optional: Configuration for Celery (adjust as needed)
celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
    timezone='UTC'
)
