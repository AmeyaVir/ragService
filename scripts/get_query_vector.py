#!/usr/bin/env python3
"""
Utility script to generate the embedding vector for a given query text.
The output vector is a raw JSON array of 384 floats, ready to be copied
and used directly in a Qdrant cURL search request.
"""
import asyncio
import os
import sys
import json
from sentence_transformers import SentenceTransformer

# --- Path and Environment Setup (CRITICAL FIX FOR STANDALONE SCRIPTS) ---
# 1. Determine the project root directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, '..')

# 2. Add the project root to the Python path to ensure package imports work
sys.path.insert(0, PROJECT_ROOT)

# 3. Load environment variables (needed for other scripts, good practice here)
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# --- Configuration ---
# The model used for indexing (must match the model used in RAGService)
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'

def get_query_vector(query: str):
    """Generates and prints the embedding vector for the query."""
    print(f"--- Generating Vector for Query: '{query}' ---")
    
    try:
        # Load the embedding model
        # This will automatically download weights if they aren't present
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
        # Generate embedding vector
        vector = model.encode(query, convert_to_numpy=True).tolist()
        
        print(f"✅ Vector Generated (Dimension: {len(vector)})")
        print("\n--- RAW VECTOR OUTPUT (Copy this entire array for cURL) ---")
        
        # Print the vector as a dense JSON array
        print(json.dumps(vector))
        
        print("----------------------------------------------------------")

    except Exception as e:
        print(f"\n❌ FATAL ERROR: Failed to generate vector.")
        print(f"Error: {e!r}")
        print("Check if 'sentence-transformers' is installed in your environment.")


if __name__ == "__main__":
    # Use the problematic query for the test
    query_text = "What technologies does the Technical Architecture document mention?"
    
    # Run the synchronous function directly
    get_query_vector(query_text)
