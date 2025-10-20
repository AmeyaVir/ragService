#!/usr/bin/env python3
"""
Utility script to force the deletion and recreation of the Qdrant
'rag_documents' collection, simulating the initial worker setup.
"""
import os
import sys
import asyncio
import structlog
import logging

# --- Path and Configuration Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, "backend/.env"))

# Import the service responsible for setup
from backend.services.qdrant_service import QdrantService 
from backend.config import get_settings # Needed for logging initialization

def configure_logger():
    """Sets up minimal logging to see the service's delete/create messages."""
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(min_level=logging.INFO),
        cache_logger_on_first_use=True,
    )

def clear_and_recreate_collection():
    print("--- Forcing Qdrant Collection Reset ---")
    
    # Initializing QdrantService automatically runs setup_collection_if_needed()
    # which contains the aggressive deletion/recreation logic.
    try:
        QdrantService()
        print("✅ Qdrant collection reset successfully.")
        print("The 'rag_documents' collection is now empty and ready for indexing.")
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to or reset Qdrant.")
        print(f"Ensure Qdrant is running at {get_settings().qdrant_url}. Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    configure_logger()
    clear_and_recreate_collection()
