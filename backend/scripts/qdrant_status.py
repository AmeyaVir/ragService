#!/usr/bin/env python3
"""
Checks the status and vector count in the Qdrant collection.
"""
import sys
import os
import asyncio
import time

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.qdrant_service import QdrantService
import structlog
from qdrant_client.http.exceptions import UnexpectedResponse

logger = structlog.get_logger()

# Helper to run the synchronous service check safely
async def check_status():
    print("Initializing Qdrant Service...")
    
    # Initialize the service, which also calls setup_collection_if_needed()
    try:
        qdrant_service = QdrantService()
        
        # Give Qdrant a moment to ensure the collection is fully created after setup
        await asyncio.sleep(2) 

        collection_info = qdrant_service.client.get_collection(
            collection_name=qdrant_service.COLLECTION_NAME
        )
        
        vector_count = collection_info.points_count

        print("\n=============================================")
        print(f"✅ Qdrant Collection: {qdrant_service.COLLECTION_NAME}")
        print(f"✅ Total Vectors Indexed: {vector_count}")
        print(f"   Status: {collection_info.status.value}")
        print(f"   Vectors Size: {qdrant_service.VECTOR_SIZE}")
        print("=============================================\n")

    except UnexpectedResponse as e:
        print(f"\n❌ ERROR: Qdrant service appears unavailable or collection info failed.")
        print(f"   Ensure Qdrant is running at {qdrant_service.qdrant_url}")
        print(f"   Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Configure logging for the script environment
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.JSONRenderer(indent=None, sort_keys=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(min_level=structlog.CRITICAL),
        cache_logger_on_first_use=True,
    )
    
    # Run the check
    asyncio.run(check_status())
