#!/usr/bin/env python3
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Dict, Any
from starlette.responses import RedirectResponse
import httpx
from sqlalchemy import update, text 
from sqlalchemy.sql import func
import sys 
import asyncio 
# FIX: Removed the failing import: from sqlalchemy.ext.asyncio import run_sync

# CRITICAL FIX: Changed to multi-level parent relative import (..)
from ...config import get_settings
# CRITICAL FIX: We will now use get_db_session for the update
from ...database import get_db_session, User 

router = APIRouter()
security = HTTPBearer()
settings = get_settings()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """Authenticate user and return access token"""
    # Demo authentication - always succeed for demo purposes
    if login_data.username == "demo" and login_data.password == "demo":
        return TokenResponse(
            access_token="demo_token_12345",
            token_type="bearer"
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


@router.post("/logout")
async def logout():
    """Logout user"""
    return {"message": "Successfully logged out"}


@router.get("/me")
async def get_current_user():
    """Get current user information"""
    # IMPORTANT: The 'id' here must match the DB ID for the demo user
    return {
        "id": "1", 
        "username": "demo",
        "name": "Demo User", 
        "email": "demo@example.com",
        "tenant_id": "demo"
    }

# ----------------------------------------------------------------------
# NEW: Google Drive OAuth Flow Endpoints
# ----------------------------------------------------------------------

@router.get("/google/login", tags=["Google Drive Auth"])
async def google_login():
    """Redirects user to Google for Drive authorization (Step 1)."""
    # This must include access_type=offline and prompt=consent to get a Refresh Token
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={settings.GOOGLE_OAUTH_CLIENT_ID}&"
        f"redirect_uri={settings.GOOGLE_OAUTH_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={settings.GOOGLE_OAUTH_SCOPES}&"
        f"access_type=offline&"  # CRITICAL: Ensures a Refresh Token is issued
        f"prompt=consent"       # CRITICAL: Ensures consent is shown (and refresh token for non-first time)
    )
    return RedirectResponse(url=google_auth_url)

@router.get("/google/callback", tags=["Google Drive Auth"])
async def google_callback(request: Request, code: str):
    """Receives auth code, exchanges it for tokens, and saves the refresh token (Step 2)."""
    token_url = "https://oauth2.googleapis.com/token"
    frontend_url = "http://localhost:3000"
    user_id = 1 # DEMO HARDCODE for 'demo' user

    # CRITICAL FIX: Restore the token_data definition
    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        # 1. Exchange authorization code for tokens
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=token_data) 
            response.raise_for_status()
            tokens = response.json()

        refresh_token = tokens.get("refresh_token")
        
        if not refresh_token:
            pass 

        # 2. CRITICAL FIX: Use the native ASYNC DB session directly to perform the update.
        # This completely bypasses the complex, failing synchronous threading logic.
        if refresh_token:
            async with get_db_session() as db:
                # Execute the update statement using the ORM update syntax
                stmt = update(User).where(User.id == user_id).values(
                    gdrive_refresh_token=refresh_token,
                    gdrive_linked_at=func.now()
                )
                await db.execute(stmt)
                await db.commit() # This commit is now running in the correct async context

            # Diagnostic print (confirms the entire transaction block completed)
            print(f"\n--- DIAGNOSTIC: ASYNC DB COMMIT COMPLETED FOR USER {user_id} ---", file=sys.stderr)
            
        # Redirect back to the frontend on success
        return RedirectResponse(url=f"{frontend_url}?google_auth=success")

    except httpx.HTTPStatusError as e:
        # This catches Google API errors
        return RedirectResponse(url=f"{frontend_url}?google_auth=error&detail=HTTP Error {e.response.status_code}")
    except Exception as e:
        # CRITICAL DEBUG STEP: Log the actual exception that is preventing commit
        print(f"\n--- FATAL CALLBACK EXCEPTION ---\nError Type: {type(e).__name__}\nDetail: {e}\n----------------------------------", file=sys.stderr)
        import traceback; traceback.print_exc(file=sys.stderr) # Print the full stack trace
        return RedirectResponse(url=f"{frontend_url}?google_auth=error&detail=Internal DB Failure")
