#!/usr/bin/env python3
"""
Utility script to check the status of the Qdrant vector database and perform
a manual test search against the rag_documents collection.
"""
import asyncio
import os
import sys

# --- FINAL PATH FIX: Insert project root to ensure backend imports work ---
# Get the absolute path to the project root directory (one level up from 'scripts')
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Insert this path at the beginning of the system path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# --------------------------------------------------------------------------

import structlog
import json
import logging
from typing import Any, Dict, List
from dotenv import load_dotenv

# Load environment variables from the project root .env file
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# Import services (should now work because PROJECT_ROOT is on sys.path)
from backend.services.qdrant_service import QdrantService
from backend.services.rag_service import RAGService # Needed for search test

# --- Configuration ---
# Set the log level for this script to prevent verbose logging from dependencies
def configure_structlog_for_script():
    # Only show critical logs to prevent Qdrant and other libs from spamming console
    logging.basicConfig(level=logging.CRITICAL)
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(min_level=logging.CRITICAL),
        cache_logger_on_first_use=False,
    )

def _get_nested_value(data: Dict, path: str, default: Any = "N/A"):
    """Safely retrieves a value from a nested dictionary path."""
    keys = path.split('.')
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
    return current if current is not None else default

async def check_qdrant_status(test_query: str):
    """Initializes QdrantService and prints collection status and performs test search."""
    print("Initializing Qdrant Service...")

    qdrant_service: QdrantService = None
    rag_service: RAGService = None
    collection_name = "rag_documents"

    try:
        # 1. Initialize services
        qdrant_service = QdrantService(collection_name=collection_name)
        rag_service = RAGService()
        
        # 2. Get collection info
        collection_info = await asyncio.to_thread(
            qdrant_service.client.get_collection,
            collection_name=collection_name
        )
        
        # Convert to dictionary for safe traversal (using model_dump(mode='json') is safer if available)
        try:
            info_dict = collection_info.dict()
        except AttributeError:
            # Fallback for older Pydantic models
            info_dict = collection_info.__dict__
        
        # 3. Extract status details
        status = info_dict.get('status', 'UNKNOWN')
        vector_count = _get_nested_value(info_dict, 'points_count', 0)
        
        # Access vector dimension safely
        vector_size = "N/A"
        if info_dict.get('config') and info_dict['config'].get('params') and info_dict['config']['params'].get('vectors_config'):
            vector_config = info_dict['config']['params']['vectors_config']
            # Handles both single vector and multi-vector config structures
            if isinstance(vector_config, dict) and vector_config.get('size'):
                 vector_size = vector_config['size']
            elif isinstance(vector_config, dict) and 'default' in vector_config:
                 vector_size = _get_nested_value(vector_config['default'], 'size')
        
        shard_count = _get_nested_value(info_dict, 'shards_count', 1) # Assumes 'shards_count' exists
        indexing_progress = _get_nested_value(info_dict, 'indexed_vectors_count', 0) / (vector_count or 1) * 100
        disk_used = _get_nested_value(info_dict, 'disk_usage_bytes', 'N/A')
        
        print(f"\n=======================================================")
        print(f"✅ Qdrant Collection: {collection_name}")
        print(f"=======================================================")
        print(f"🔹 Status: {status}")
        print(f"🔹 Total Vectors Indexed: {vector_count}")
        print(f"🔹 Vector Size: {vector_size}")
        print(f"🔹 Shard Count: {shard_count}")
        print(f"🔹 Indexing Progress: {indexing_progress:.1f}%")
        # Convert bytes to MB for display
        disk_display = f"{disk_used / (1024 * 1024):.2f} MB" if isinstance(disk_used, (int, float)) else disk_used
        print(f"🔹 Disk Used: {disk_display}")
        print(f"=======================================================")
        
        # --- RAG Retrieval Test ---
        print(f"\n--- RAG Retrieval Test: Querying '{test_query}' ---")
        
        if rag_service:
            context = await rag_service.retrieve_context(
                query=test_query,
                tenant_id="demo",
                project_ids=["mars_project"],
                limit=3
            )
            
            if context:
                print(f"✅ Retrieved {len(context)} context item(s) from Qdrant.")
                for i, ctx in enumerate(context):
                    print(f"--- Chunk {i+1} (Score: {ctx['score']:.4f}) ---")
                    print(f"Source: {ctx['source_file']} ({ctx['project_id']})")
                    print(f"Content: {ctx['content'][:200]}...")
            else:
                print("❌ Retrieval failed or returned no context.")
        
        print("-------------------------------------------------------")


    except Exception as e:
        print(f"\n=======================================================")
        print(f"❌ FAILED TO CONNECT OR RETRIEVE QDRANT STATUS")
        print(f"=======================================================")
        print(f"Error: {e!r}")
        print(f"")
        print("Check the following:")
        print("1. Is the Qdrant server running and accessible at the URL in your .env file?")
        print("2. Are all required environment variables set in .env?")
        print("3. Are you running this script from the project root or the 'scripts' directory?")
        print("=======================================================")


if __name__ == "__main__":
    configure_structlog_for_script()
    # Define the test query here
    query = "What technologies does the Technical Architecture document mention?"
    
    try:
        asyncio.run(check_qdrant_status(query))
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
             print("\nRuntime Error: Script cannot be run while the Celery worker or FastAPI server is running in the same terminal session.")
             print("Please run this script after stopping all other local services.")
        else:
             raise
