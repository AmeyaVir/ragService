#!/usr/bin/env python3
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import Response, JSONResponse
from typing import Dict, Any, Union
import structlog
import uuid

# Use multi-level parent relative imports
from ...services.artifact_service import ArtifactService
# CRITICAL FIX: DO NOT import from main here. We will access services via Request.app.state

router = APIRouter()
logger = structlog.get_logger()

# --- Mock Data Store (In a real system, this would be S3 or GCS) ---
# Stores temporary artifact bytes with a UUID key and metadata
ARTIFACT_CACHE: Dict[str, Dict[str, Union[bytes, str]]] = {} 
# -------------------------------------------------------------------

def add_artifact_to_cache(file_bytes: bytes, filename: str, mime_type: str) -> Dict[str, str]:
    """Stores the generated file in a temporary cache and returns metadata."""
    file_id = str(uuid.uuid4())
    ARTIFACT_CACHE[file_id] = {
        "bytes": file_bytes,
        "filename": filename,
        "mime_type": mime_type
    }
    
    # Return metadata for the chat response
    return {
        "id": file_id,
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": str(len(file_bytes))
    }

@router.post("/generate")
async def generate_artifact_endpoint(
    request_data: Dict[str, Union[str, Dict[str, Any]]],
    request: Request # Inject the request object to access app state
):
    """
    Called internally by the AgentOrchestrator to create a file 
    and send a temporary download link via WebSocket.
    """
    # CRITICAL FIX: Access services directly from app state and the global manager instance
    artifact_service: ArtifactService = request.app.state.artifact_service
    manager = request.app.state.manager # manager is now stored on app.state in main.py

    artifact_type = request_data.get("artifact_type")
    project_name = request_data.get("project_name")
    session_id = request_data.get("session_id")
    data = request_data.get("data", {})

    if not all([artifact_type, project_name, session_id]):
        raise HTTPException(status_code=400, detail="Missing artifact_type, project_name, or session_id.")

    try:
        file_bytes = await artifact_service.generate_artifact(artifact_type, project_name, data)
        
        if file_bytes is None:
            raise HTTPException(status_code=500, detail="Artifact generation failed internally.")

        # Determine file metadata based on type
        mime_type = "application/octet-stream"
        if artifact_type == "excel_risk_register":
            filename = f"{project_name}_Risk_Register.xlsx"
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif artifact_type == "word_status_report":
            filename = f"{project_name}_Status_Report.docx"
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif artifact_type == "pptx_executive_pitch":
            filename = f"{project_name}_Executive_Pitch.pptx"
            mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        else:
            filename = f"{project_name}_Artifact.bin"

        metadata = add_artifact_to_cache(file_bytes, filename, mime_type)
        
        # Send a direct WebSocket message to the user about the generated artifact
        await manager.send_message(session_id, {
            "type": "artifact_generated",
            "session_id": session_id,
            "artifact": {
                "id": metadata["id"],
                "filename": metadata["filename"],
                "mime_type": metadata["mime_type"],
                "download_url": f"/api/v1/artifacts/download/{metadata['id']}" # Relative path
            }
        })

        # Return a simple confirmation to the orchestrator
        return {"status": "success", "artifact_id": metadata["id"]}

    except Exception as e:
        logger.error("Artifact generation endpoint failed.", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate artifact: {e}")

@router.get("/download/{file_id}")
async def download_artifact_endpoint(file_id: str):
    """Retrieves and serves the temporary artifact file."""
    if file_id not in ARTIFACT_CACHE:
        raise HTTPException(status_code=404, detail="File not found or expired.")

    # Retrieve data from cache
    artifact_data = ARTIFACT_CACHE[file_id]
    file_bytes = artifact_data["bytes"]
    filename = artifact_data["filename"]
    mime_type = artifact_data["mime_type"]
    
    # Optional: Delete from cache after download to clean up mock storage
    del ARTIFACT_CACHE[file_id] 

    return Response(
        content=file_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Content-Length": str(len(file_bytes))
        }
    )
