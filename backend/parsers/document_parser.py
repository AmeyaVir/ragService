#!/usr/bin/env python3
from typing import List, Dict, Any, Optional
import io
import structlog
import nltk # Import NLTK

# Import the core library for document parsing
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import Text, Title

logger = structlog.get_logger()

# Define maximum size for chunks to control vector size
MAX_CHUNK_CHARS = 1024

class DocumentParser:
    """
    Handles parsing binary document content from Google Drive, cleaning it, 
    and chunking it into smaller, semantically meaningful pieces.
    """
    def __init__(self):
        """Initializes the parser and ensures NLTK resources are available."""
        self._ensure_nltk_resources()

    def _ensure_nltk_resources(self):
        """
        Checks for required NLTK resources and downloads them if necessary.
        This fixes the Resource averaged_perceptron_tagger_eng not found error.
        It uses LookupError, which is more robust across NLTK versions.
        """
        required_resources = ['taggers/averaged_perceptron_tagger_eng']
        
        for resource in required_resources:
            try:
                # Check if the resource is already downloaded
                nltk.data.find(resource)
            except LookupError:
                # LookupError is the most reliable exception when a resource is missing.
                logger.info("NLTK resource not found. Downloading now.", resource=resource)
                try:
                    # Download only the missing resource (e.g., 'averaged_perceptron_tagger_eng')
                    resource_name = resource.split('/')[-1]
                    nltk.download(resource_name, quiet=True)
                    logger.info("NLTK resource downloaded successfully.", resource=resource)
                except Exception as e:
                    logger.error("Failed to download NLTK resource.", resource=resource, error=str(e))
            except Exception as e:
                # Catch any other unexpected NLTK exceptions during find
                logger.error("Unexpected NLTK error during resource check.", resource=resource, error=str(e))


    def parse_and_chunk(self, file_content: bytes, filename: str, mime_type: str, project_id: str, tenant_id: str) -> List[str]:
        """
        Parses binary file content into elements and chunks them by title.

        Args:
            file_content: The raw bytes of the file downloaded from GDrive.
            filename: The name of the file (used for logging/context).
            mime_type: The MIME type of the file.
            project_id: The ID of the associated project.
            tenant_id: The ID of the associated tenant.

        Returns:
            A list of strings, where each string is a document chunk.
        """
        logger.info("Starting parsing and chunking.", filename=filename, project_id=project_id)
        
        try:
            # 1. Partition the file content into elements
            elements = partition(
                file=io.BytesIO(file_content), 
                file_filename=filename,
                content_type=mime_type
            )

            # 2. Chunk the elements by title (a common strategy for RAG)
            chunks = chunk_by_title(
                elements=elements, 
                max_characters=MAX_CHUNK_CHARS,
                new_after_n_chars=MAX_CHUNK_CHARS,
                combine_text_under_n_chars=256
            )
            
            # 3. Extract clean text from the resulting chunks
            text_chunks = [chunk.text for chunk in chunks if isinstance(chunk, (Text, Title))]

            logger.info("Finished parsing and chunking.", 
                        filename=filename, 
                        total_chunks=len(text_chunks))
                        
            return text_chunks

        except Exception as e:
            logger.error("Error during parsing or chunking.", 
                         filename=filename, 
                         error=str(e),
                         project_id=project_id,
                         tenant_id=tenant_id)
            return []
