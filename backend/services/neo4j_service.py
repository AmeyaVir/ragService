#!/usr/bin/env python3
import asyncio
from typing import Dict, Any
from neo4j import AsyncGraphDatabase, AsyncDriver
import structlog

# CORRECTED: Use parent-level import (..) to find config.py
from ..config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class Neo4jService:
    # ... (content remains the same below the import block)
    """
    Handles connection and operations with the Neo4j Knowledge Graph.
    
    The driver is initialized within the methods that use it (via an async context manager) 
    to prevent "attached to a different loop" errors when running inside Celery's asyncio.run().
    """
    def __init__(self):
        # We only store configuration here, not the driver instance
        self.uri = settings.neo4j_url
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        logger.info("Neo4j Service configured.")

    async def _get_driver_and_session(self):
        """Helper to create and yield an async session within a driver context."""
        driver: AsyncDriver = None
        
        try:
            # Create driver inside the async function to tie it to the current loop
            driver = AsyncGraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            async with driver.session() as session:
                yield session
        except Exception as e:
            logger.error("Failed to establish Neo4j session.", uri=self.uri, error=str(e))
            raise e
        finally:
            if driver:
                await driver.close()


    async def add_document_node(self, metadata: Dict[str, Any]):
        """
        Creates a Document node and links it to its Project and Tenant.
        
        Args:
            metadata: Contains document details (document_id, filename, project_id, tenant_id, etc.)
        """
        cypher_query = """
        MERGE (t:Tenant {tenant_id: $tenant_id})
        ON CREATE SET t.created_at = datetime()
        
        MERGE (p:Project {project_id: $project_id})
        ON CREATE SET p.name = $project_id, p.created_at = datetime()
        
        MERGE (t)-[:HAS_PROJECT]->(p)
        
        MERGE (d:Document {document_id: $document_id})
        ON CREATE SET 
            d.filename = $filename, 
            d.mime_type = $mime_type, 
            d.size_bytes = $size_bytes,
            d.chunk_count = $chunk_count,
            d.created_at = datetime()
            
        MERGE (p)-[:HAS_DOCUMENT]->(d)
        """
        
        try:
            # Use the generator for context management
            async for session in self._get_driver_and_session():
                await session.run(cypher_query, **metadata)
            logger.info("Document node created/merged in Neo4j.", document_id=metadata.get('document_id'))
            
        except Exception as e:
            logger.error("Failed to add document node to Neo4j.", error=str(e), document_id=metadata.get('document_id'))
            # Re-raise the exception so it propagates to Celery for logging/retrying
            raise e
