#!/usr/bin/env python3
"""
Utility script to run an End-to-End RAG query (Embed -> Retrieve -> Generate) 
outside of the FastAPI server to diagnose retrieval and grounding issues.
"""
import asyncio
import os
import sys
import structlog
import logging
from typing import Any, Dict, List

# --- Path and Environment Setup (CRITICAL FIX FOR ModuleNotFoundError) ---
# 1. Determine the project root directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, '..')

# 2. Add the project root to the Python path to resolve 'backend' imports
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 3. Load environment variables from the project root .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, 'backend/.env')) 

# Import services using the absolute package path (guaranteed to work)
from backend.services.rag_service import RAGService 
from backend.services.qdrant_service import QdrantService 
from backend.config import get_settings 


# --- Configuration ---
def configure_structlog_for_script():
    """Configures structlog to be non-verbose for simple script output."""
    logging.basicConfig(level=logging.CRITICAL)
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks, 
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(min_level=logging.CRITICAL),
        cache_logger_on_first_use=False,
    )

async def test_rag_e2e(query: str):
    """Runs a full RAG cycle (retrieve and generate)."""
    print(f"\n=======================================================")
    print(f"       END-TO-END RAG DIAGNOSTIC TEST")
    print(f"=======================================================")
    print(f"Query: {query}")
    
    # --- CONFIGURATION MATCHING LAST SYNC ---
    # Inside scripts/test_e2e_rag.py (Update the TEST_PROJECT_IDS variable)
    TEST_PROJECT_IDS = ["6"]  # FINAL TEST: Use the correct indexed project ID
    TEST_TENANT_ID = "1"
    # ... 

    try:
        # 1. Initialize RAG Service (This initializes Qdrant and LLM services too)
        rag_service = RAGService()
        
        # 2. Retrieve Context from Qdrant
        print("\n--- Step 1: Context Retrieval (Qdrant) ---")
        context = await rag_service.retrieve_context(
                query=query,
                tenant_id=TEST_TENANT_ID,
                project_ids=TEST_PROJECT_IDS, # This is now []
                limit=5
        )

        if not context:
            print(f"\u274c Retrieval failed: No relevant context chunks were returned by Qdrant for project {TEST_PROJECT_IDS} (Tenant: {TEST_TENANT_ID}).")
            print("   (Reason: Poor semantic match or data not fully indexed.)")
            return
        
        # 3. Print Retrieved Context (The diagnostic data we need!)
        print(f"\u2705 Retrieved {len(context)} context item(s).")
        print("\n--- Step 2: Retrieved Context (Raw Data) ---")
        for i, ctx in enumerate(context):
            print(f"--- Chunk {i+1} (Score: {ctx['score']:.4f}) ---")
            print(f"Source: {ctx['source_file']} (Project ID: {ctx['project_id']})")
            # Print the raw content retrieved, limiting length for readability
            print(f"Content: {ctx['content'].strip()}")
            print("-" * 20)

        # 4. Generate Final Response using LLM
        print("\n--- Step 3: LLM Grounded Generation ---")
        response_data = await rag_service.generate_response(
            query=query,
            context=context
        )
        
        print(f"\u2705 Generated Answer: {response_data['response'].strip()}")
        print(f"Sources Used: {[s['file'] for s in response_data['sources']]}")
        print("\n=======================================================")

    except Exception as e:
        print(f"\n\u274c FATAL RAG ERROR: {e!r}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    configure_structlog_for_script()
    
    # Use a query that should match your 'Diatomite Data Overview.txt' file
    query = "Summarize the objectives for the Diatomite project based on the overview document." 
    
    try:
        asyncio.run(test_rag_e2e(query))
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
             print("\nRuntime Error: Script cannot be run while the Celery worker or FastAPI server is running in the same terminal session.")
             print("Please stop all services and rerun this script.")
        else:
             raise
