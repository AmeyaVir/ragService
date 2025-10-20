import asyncio
from typing import Dict, Any, List
import os
import structlog
# NEW IMPORTS
from celery.signals import worker_process_init 
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.engine.base import Engine as SyncEngine

# CRITICAL FIX: Use parent-level relative imports (..)
from ..celery_app import celery_app
from ..database import get_db_session, User, init_db, get_initialized_engine # Import init_db and get_initialized_engine
from ..services.gdrive_service import GoogleDriveService 
from ..services.rag_service import RAGService         
from ..services.neo4j_service import Neo4jService     
from ..parsers.document_parser import DocumentParser   
from ..config import get_settings # Needed to access DB URL for sync engine

logger = structlog.get_logger()
settings = get_settings()

# Initialize services outside of tasks for reuse
gdrive_service = GoogleDriveService()
rag_service = RAGService()
neo4j_service = Neo4jService()

# Engine instance must be accessible for sync access
celery_db_engine: SyncEngine | None = None

@worker_process_init.connect
def setup_db_for_celery(**kwargs):
    global celery_db_engine
    
    # CRITICAL FIX: Initialize a SYNCHRONOUS engine for Celery tasks only.
    # This avoids the "different loop" error by not using the async driver.
    try:
        db_url_sync = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        
        celery_db_engine = create_engine(
            db_url_sync,
            echo=False, 
            connect_args={"sslmode": "disable"}
        )
        # We don't need to run init_db() here, as the sync engine is enough for queries.
        
        with celery_db_engine.connect():
             logger.info("Celery worker SYNCHRONOUS DB engine initialized successfully.")
             
    except Exception as e:
        logger.error("FATAL: Celery worker failed to initialize DB engine.", error=str(e))
        raise # Fail hard if the DB can't connect


# Helper function to run the token fetching logic synchronously
def _fetch_user_refresh_token_sync(user_id: int) -> str | None:
    """Synchronous part to fetch refresh token from DB using the stable sync engine."""
    
    if celery_db_engine is None:
        raise RuntimeError("Celery DB engine was not initialized on worker startup.")
        
    try:
        with Session(celery_db_engine) as session:
            # Execute the query using the synchronous session
            result = session.scalar(select(User.gdrive_refresh_token).where(User.id == user_id))
            # Commit not needed as this is a read, but session handles context.
            return result
    except Exception as e:
        logger.error("Error during synchronous token fetch.", error=str(e))
        raise # Re-raise for task retry


@celery_app.task(name='document.process_document', bind=True, max_retries=3)
def process_document_task(self, file_meta: Dict[str, Any], project_id: str, tenant_id: str, refresh_token: str):
    """
    Downloads, parses, chunks, embeds, and indexes a single document.
    """
    document_id = file_meta.get('id')
    filename = file_meta.get('name')
    mime_type = file_meta.get('mimeType')

    logger.info("Starting document processing.", document_id=document_id, filename=filename)

    try:
        # 1. Download File Content (Async call must be run synchronously and pass the token)
        file_content_coroutine = gdrive_service.download_file(file_meta['id'], refresh_token)
        file_content = asyncio.run(file_content_coroutine)

        if not file_content:
            logger.error("Skipping file: Failed to download content (check user's GDrive token/permissions).", document_id=document_id)
            return

        # 2. Parse and Chunk Document
        parser = DocumentParser()
        chunks = parser.parse_and_chunk(
            file_content=file_content,
            filename=filename,
            mime_type=mime_type,
            project_id=project_id,
            tenant_id=tenant_id
        )

        if not chunks:
            logger.warning("Skipping file: No content chunks extracted.", document_id=document_id)
            return

        # Augment chunks with metadata required for indexing
        augmented_chunks = []
        for i, chunk in enumerate(chunks):
            augmented_chunks.append({
                "content": chunk,
                "document_id": document_id,
                "project_id": project_id,
                "tenant_id": tenant_id,
                "source_file": filename,
                "chunk_id": f"{document_id}-{i}",
            })

        # 3. Embed and Index in Qdrant (Vector DB)
        index_coroutine = rag_service.index_document_chunks(augmented_chunks)
        asyncio.run(index_coroutine) 
        logger.info("Successfully indexed document chunks in Qdrant.", document_id=document_id, chunk_count=len(augmented_chunks))

        # 4. Index Metadata in Neo4j (Knowledge Graph)
        document_metadata = {
            "document_id": document_id, 
            "filename": filename,
            "project_id": project_id,
            "tenant_id": tenant_id,
            "mime_type": mime_type,
            "size_bytes": file_meta.get('size'),
            "chunk_count": len(augmented_chunks)
        }
        # Async call must be run synchronously
        asyncio.run(neo4j_service.add_document_node(document_metadata))
        logger.info("Successfully indexed document metadata in Neo4j.", document_id=document_id)

    except Exception as exc:
        logger.error("Failed to process document.", document_id=document_id, error=str(exc))
        # Retry the task upon failure
        raise self.retry(exc=exc, countdown=5)


@celery_app.task(name='document.start_gdrive_sync')
def start_gdrive_sync_task(project_id: str, folder_id: str, tenant_id: str, user_id: int):
    """
    Main entry point for Google Drive synchronization. Lists files and dispatches
    individual processing tasks.
    """
    logger.info("Starting GDrive sync task", folder_id=folder_id, project_id=project_id, tenant_id=tenant_id, user_id=user_id)
    
    # 1. Fetch the user's Refresh Token from the database (Synchronous wrapper)
    try:
        # FINAL FIX: Use the stable synchronous fetch utility
        refresh_token = _fetch_user_refresh_token_sync(user_id)
    except Exception as e:
        logger.error("Failed to retrieve user token from database.", error=str(e), user_id=user_id)
        return # Abort sync
    
    if not refresh_token:
        logger.error("Gdrive sync failed: No refresh token found for user.", user_id=user_id)
        return # Abort sync

    # 2. List files (Async call must be run synchronously and pass the token)
    files_metadata_coroutine = gdrive_service.list_files_in_folder(folder_id, refresh_token)
    
    # Run the coroutine synchronously to get the list of files
    try:
        files_metadata: List[Dict[str, Any]] = asyncio.run(files_metadata_coroutine)
    except Exception as e:
        logger.error("Failed to list files from GDrive.", error=str(e), folder_id=folder_id)
        return

    if not files_metadata:
        logger.warning("No files found or unable to list files.", folder_id=folder_id)
        return

    logger.info("Found files to process.", file_count=len(files_metadata), project_id=project_id)

    # 3. Dispatch tasks for each document
    for file_meta in files_metadata:
        # Check if file type is supported (e.g., skip folders)
        if file_meta.get('mimeType') != 'application/vnd.google-apps.folder':
            # MODIFIED: Pass the refresh_token to the document processing task
            process_document_task.delay(
                file_meta=file_meta,
                project_id=project_id,
                tenant_id=tenant_id,
                refresh_token=refresh_token # Pass token to next task
            )
            logger.info("Dispatched processing task.", file_id=file_meta['id'], filename=file_meta['name'])
        else:
            logger.info("Skipping folder in sync.", filename=file_meta['name'])
