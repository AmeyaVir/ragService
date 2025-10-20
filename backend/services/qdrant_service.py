import asyncio
import os
import structlog
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from typing import List, Dict, Any 
import hashlib 

from ..config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# The size of the 'all-MiniLM-L6-v2' embedding model
EMBEDDING_DIMENSION = 384 
# Set collection name as a class constant for better access
COLLECTION_NAME = "rag_documents"

def generate_stable_id(input_string: str) -> int:
    """Generates a stable 64-bit integer ID from a string using SHA-256."""
    # Use SHA-256 for stable hashing across processes/runs
    digest = hashlib.sha256(input_string.encode()).digest()
    # Take the first 8 bytes and convert them to an integer
    # A 64-bit int is safe for Qdrant point IDs
    return int.from_bytes(digest[:8], byteorder='big')

class QdrantService:
    def __init__(self, collection_name: str = COLLECTION_NAME):
        self.collection_name = collection_name
        self.client = QdrantClient(url=settings.qdrant_url)
        self.setup_collection_if_needed() 

    def setup_collection_if_needed(self):
        """
        Ensures the Qdrant collection exists.
        The aggressive deletion logic is REMOVED to allow data persistence.
        """
        try:
            # Check if the collection exists
            self.client.get_collection(collection_name=self.collection_name)
            logger.info("Qdrant collection found. Skipping recreation.")
            
        except UnexpectedResponse:
            # Collection was not found, so create it
            logger.info("Qdrant collection not found. Creating now.", collection_name=self.collection_name)
            
            # 1. Create the collection
            try:
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=models.Distance.COSINE
                    ),
                )
                logger.info("Qdrant collection created successfully", dimension=EMBEDDING_DIMENSION)

                # 2. Create payload indices for filtering (project_id and tenant_id)
                self.client.create_payload_index(
                    collection_name=self.collection_name, 
                    field_name="project_id", 
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                self.client.create_payload_index(
                    collection_name=self.collection_name, 
                    field_name="tenant_id", 
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                logger.info("Created payload indices for project_id and tenant_id.")
                
            except Exception as e:
                logger.error("Failed to create Qdrant collection or indices", error=str(e))
                raise
        except Exception as e:
             logger.error("General error during Qdrant initialization check", error=str(e))
             raise # Re-raise any other unexpected error

    # RENAMED to index_points for clarity and to align with RAGService
    async def index_points(self, points_data: List[Dict[str, Any]]):
        """Indexes document chunks into Qdrant using the pre-calculated embeddings."""
        if not points_data:
            return

        points = []
        for point_data in points_data:
            # Ensure the structure matches PointStruct
            points.append(
                models.PointStruct(
                    # Use stable hash for ID generation
                    id=generate_stable_id(point_data["payload"]["chunk_id"]), 
                    vector=point_data["vector"],
                    payload=point_data["payload"] 
                )
            )

        # Upload points to the collection
        operation_info = await asyncio.to_thread(
            self.client.upsert,
            collection_name=self.collection_name,
            wait=True,
            points=points
        )
        logger.info("Indexed chunks to Qdrant", status=operation_info.status.value, count=len(points))
        return operation_info
    
    
    async def search_vectors(self, query_embedding: list[float], project_ids: list[str], tenant_id: str, limit: int = 5) -> list[dict[str, any]]:
        """Performs vector search with project and tenant filtering."""

        # Define the filter to restrict search to specific project IDs AND the tenant ID
        # Only allow results that match the tenant_id AND one of the project_ids
        search_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="tenant_id",
                    match=models.MatchValue(value=tenant_id)
                )
            ],
            should=[
                models.FieldCondition(
                    key="project_id",
                    match=models.MatchValue(value=pid)
                ) for pid in project_ids if pid # Filter out empty project IDs
            ]
        )
        
        # If no project IDs are passed, remove the 'should' filter to search all of the tenant's data
        if not project_ids or all(not pid for pid in project_ids):
            search_filter.should = []

        # Perform the search
        search_result = await asyncio.to_thread(
            self.client.search,
            collection_name=self.collection_name,
            query_vector=query_embedding, 
            query_filter=search_filter, # Use the constructed filter
            limit=limit,
            with_payload=True # Include the content/metadata in the result
        )

        results = []
        for hit in search_result:
            results.append({
                "score": hit.score,
                # The payload now correctly contains the original chunk data
                "payload": hit.payload 
            })
        
        return results
