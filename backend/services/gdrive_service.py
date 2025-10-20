#!/usr/bin/env python3
import io
import asyncio
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials 
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request 
import structlog

from ..config import get_settings

logger = structlog.get_logger()
settings = get_settings()

FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'

class GoogleDriveService:
    """
    Handles connection and operations with the Google Drive API using a User's Refresh Token.
    """
    def __init__(self):
        # No initial service/credentials. Will be created per call using the user's token.
        pass

    def _get_user_credentials(self, refresh_token: str):
        """Creates and refreshes Credentials object from a user's refresh token."""
        
        info = {
            'refresh_token': refresh_token,
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID, 
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET, 
            'token_uri': 'https://oauth2.googleapis.com/token'
        }
        
        creds = Credentials.from_authorized_user_info(
            info=info, 
            scopes=[settings.GOOGLE_OAUTH_SCOPES] 
        )
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            
        return creds

    def _get_service(self, refresh_token: str):
        """Helper to get a drive service instance for the user."""
        try:
            creds = self._get_user_credentials(refresh_token)
            
            if not creds.valid:
                logger.warning("User GDrive credentials invalid/revoked.", refresh_token=refresh_token[:10] + '...')
                return None
            
            return build('drive', 'v3', credentials=creds)
        except Exception as e:
            logger.error("Failed to build GDrive service from token.", error=str(e))
            return None


    async def list_files_in_folder(self, folder_id: str, refresh_token: str, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Lists all files recursively under a specified Google Drive folder using an 
        explicit traversal logic to ensure all subfolders are covered.
        """
        service = self._get_service(refresh_token)
        if not service:
            logger.warning("Google Drive service is not initialized due to invalid user token.")
            return []

        logger.info("Attempting recursive folder traversal.", root_folder_id=folder_id)
        
        all_files = []
        folders_to_visit = [folder_id]
        
        try:
            while folders_to_visit:
                current_folder_id = folders_to_visit.pop(0)
                page_token = None
                
                # Query for all items (files and folders) within the current folder
                query = (
                    f"'{current_folder_id}' in parents and "
                    f"trashed=false"
                )
                
                while True:
                    # Execute the list request
                    results = await asyncio.to_thread(
                        service.files().list,
                        q=query,
                        pageSize=page_size,
                        fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, parents)",
                        pageToken=page_token,
                        spaces='drive' 
                    )
                    results = results.execute()
                    items = results.get('files', [])

                    for item in items:
                        if item['mimeType'] == FOLDER_MIME_TYPE:
                            # If it's a folder, add it to the queue to visit later
                            folders_to_visit.append(item['id'])
                        else:
                            # If it's a file, add it to the list of documents to process
                            all_files.append(item)

                    page_token = results.get('nextPageToken', None)
                    if page_token is None:
                        break
            
            logger.info("Successfully completed recursive listing.", root_folder_id=folder_id, file_count=len(all_files))
            return all_files

        except Exception as e:
            logger.error("Failed during recursive traversal.", root_folder_id=folder_id, error=str(e))
            return []

    async def download_file(self, file_id: str, refresh_token: str) -> Optional[bytes]:
        """Downloads the content of a specific file using user's token."""
        service = self._get_service(refresh_token)
        if not service:
            logger.warning("Google Drive service is not initialized due to invalid user token.")
            return None

        logger.info("Attempting to download file.", file_id=file_id)

        try:
            # Wrap synchronous MediaIoBaseDownload in a thread
            file_io = io.BytesIO()
            
            def download_sync():
                request = service.files().get_media(fileId=file_id)
                downloader = MediaIoBaseDownload(file_io, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                return file_io.getvalue()

            file_content = await asyncio.to_thread(download_sync)
            
            logger.info("File downloaded successfully.", file_id=file_id, size_bytes=len(file_content))
            return file_content

        except Exception as e:
            logger.error("Failed to download file.", file_id=file_id, error=str(e))
            return None
