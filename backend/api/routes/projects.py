#!/usr/bin/env python3
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from pydantic import BaseModel 
from datetime import datetime
import structlog
from typing import Union 
from sqlalchemy import select, text 
from sqlalchemy.engine import Row
from sqlalchemy.sql import func 

# CRITICAL FIX: Use the stable, absolute package import path for all modules
from backend.celery_app import celery_app 
from backend.tasks.document_tasks import start_gdrive_sync_task 
from backend.database import get_db_session, User 

router = APIRouter()
logger = structlog.get_logger()

# --- Pydantic Models (MUST be defined before use) ---
class ProjectCreate(BaseModel):
    name: str
    description: str = None
    folder_id: str = None

class ProjectUpdate(BaseModel):
    folder_id: str
# ----------------------------------------------------


# Helper function to convert DB rows to a serializable dictionary
def row_to_dict(row: Row) -> Dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "status": row.status,
        "folder_id": row.folder_id,
        # Safely convert datetime objects to ISO format string
        "created_at": row.created_at.isoformat() + "Z" if hasattr(row.created_at, 'isoformat') else str(row.created_at),
        "updated_at": row.updated_at.isoformat() + "Z" if hasattr(row.updated_at, 'isoformat') else str(row.updated_at),
    }

# NEW HELPER: Check if a string is a valid integer (to prevent DataError)
def is_numeric(value: Union[str, int]) -> bool:
    if isinstance(value, int):
        return True
    if isinstance(value, str):
        return value.isdigit()
    return False


# --- Utility to handle dynamic project lookup/query generation (The core fix) ---
def build_project_lookup_query(project_id: Union[str, int], return_fields: str):
    """
    Builds the SQL query and parameters based on whether project_id is numeric (ID) or string (Name).
    
    Args:
        project_id: The ID or name passed via the URL.
        return_fields: The SELECT clause field list.
    
    Returns:
        tuple: (SQL text statement, parameters dictionary)
    """
    if is_numeric(project_id):
        # If numeric, query by ID OR name
        query = text(f"SELECT {return_fields} FROM projects WHERE id = :id OR name = :name")
        params = {"id": int(project_id), "name": str(project_id)}
    else:
        # If string, query only by name
        query = text(f"SELECT {return_fields} FROM projects WHERE name = :name")
        params = {"name": str(project_id)}
        
    return query, params


@router.get("/")
async def list_projects() -> List[Dict[str, Any]]:
    """List all projects for the current user (from DB)"""
    # DEMO: Hardcode tenant_id=1 for now
    tenant_id = 1 
    
    async with get_db_session() as db:
        # NOTE: Using raw SQL to be compatible with the init.sql schema
        result = await db.execute(
            text("SELECT * FROM projects WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        # Fetch all rows and convert to list of dictionaries
        return [row_to_dict(row) for row in result.all()]


@router.get("/{project_id}")
async def get_project(project_id: Union[int, str]) -> Dict[str, Any]:
    """Get details for a specific project (from DB)"""
    fields = "id, name, description, folder_id, status, created_at, updated_at"
    query, params = build_project_lookup_query(project_id, fields)
    
    async with get_db_session() as db:
        result = await db.execute(query, params)
        project_row = result.first()

        if not project_row:
            raise HTTPException(status_code=404, detail="Project not found")
            
        return row_to_dict(project_row)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(project: ProjectCreate):
    """Create a new project (in DB)"""
    tenant_id = 1 # DEMO HARDCODE: Link to demo tenant
    
    async with get_db_session() as db:
        # Check for existing project by name
        check_result = await db.execute(
            text("SELECT id FROM projects WHERE name = :name"),
            {"name": project.name}
        )
        if check_result.scalar():
            raise HTTPException(status_code=400, detail="Project with this name already exists")
            
        # Insert new project
        insert_stmt = text(
            "INSERT INTO projects (name, description, folder_id, tenant_id, status) "
            "VALUES (:name, :description, :folder_id, :tenant_id, 'active') RETURNING id, name, description, folder_id, status, created_at, updated_at"
        )
        
        # Execute the insert and fetch the created row
        new_project_result = await db.execute(
            insert_stmt,
            {
                "name": project.name,
                "description": project.description,
                "folder_id": project.folder_id,
                "tenant_id": tenant_id
            }
        )
        await db.commit()
        
        new_project_row = new_project_result.fetchone()
        return row_to_dict(new_project_row) if new_project_row else {"message": "Project created but could not retrieve data."}


@router.post("/{project_id}/sync")
async def sync_project(project_id: Union[int, str]):
    """
    Trigger a sync of project documents from the linked Google Drive folder.
    (Updated to fix DataError on lookup)
    """
    user_id = 1 
    tenant_id = 1 
    
    # 1. Fetch project details from DB
    fields = "id, name, description, folder_id, status, created_at, updated_at"
    query, params = build_project_lookup_query(project_id, fields)
    
    async with get_db_session() as db:
        project_result = await db.execute(query, params)
        project_row = project_result.first()

        if not project_row:
            raise HTTPException(status_code=404, detail="Project not found")

        project = row_to_dict(project_row)
        folder_id = project.get("folder_id")
        
        # 2. Check if user has linked Google Drive
        user_record = await db.execute(select(User.gdrive_refresh_token).where(User.id == user_id))
        refresh_token = user_record.scalar_one_or_none()
        
        if not refresh_token:
            raise HTTPException(status_code=400, 
                                detail="User must link their Google Drive account via /api/v1/auth/google/login before triggering sync.")

    if not folder_id:
        raise HTTPException(status_code=400, detail="Project must have a Google Drive folder_id configured to sync.")

    # Kick off the Celery task asynchronously
    task = start_gdrive_sync_task.delay(
        project_id=str(project["id"]), # Pass the DB's ID as a string for consistency in the task payload
        folder_id=folder_id, 
        tenant_id=str(tenant_id),
        user_id=user_id
    )
    logger.info("Project sync triggered", project_id=project["id"], folder_id=folder_id, task_id=task.id)

    return {
        "status": "started",
        "message": f"Sync task started for project {project_id}. Check logs for progress.",
        "task_id": task.id
    }


@router.patch("/{project_id}/folder")
async def update_folder_id(project_id: Union[int, str], update_data: ProjectUpdate):
    """Updates the GDrive folder ID for a project (in DB)"""
    
    async with get_db_session() as db:
        # Use Python logic to build the WHERE clause based on input type
        if is_numeric(project_id):
            where_clause = "WHERE id = :project_id OR name = :project_id"
            params = {"folder_id": update_data.folder_id, "project_id": int(project_id)} # Cast numeric for safety
        else:
            where_clause = "WHERE name = :project_id"
            params = {"folder_id": update_data.folder_id, "project_id": project_id}

        update_stmt = text(
            f"UPDATE projects SET folder_id = :folder_id, updated_at = NOW() {where_clause} RETURNING id, name, description, folder_id, status, created_at, updated_at"
        )
        
        result = await db.execute(
            update_stmt,
            params
        )
        await db.commit()
        
        updated_row = result.fetchone()
        
        if not updated_row:
            raise HTTPException(status_code=404, detail="Project not found")

        return {"status": "success", "project": row_to_dict(updated_row)}
