#!/usr/bin/env python3
"""
Standalone script to debug the Celery worker's synchronous database connection failure.
This version uses the fully explicit URL, assuming the .env file is now correct.
"""
import os
import sys
import structlog
import logging
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.engine.base import Engine as SyncEngine
from dotenv import load_dotenv

# --- Path and Configuration Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load environment variables
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Import the necessary backend components (Config and User model)
from backend.config import get_settings
from backend.database import User, Base 

# --- Configuration ---
settings = get_settings()
logger = structlog.get_logger()
# Logger setup remains the same

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"), structlog.processors.JSONRenderer()],
    wrapper_class=structlog.make_filtering_bound_logger(
        min_level=logging.INFO
    ),
    cache_logger_on_first_use=True,
)


def init_sync_db_engine() -> SyncEngine:
    """Initializes a synchronous DB engine using the fixed database URL."""
    
    # CRITICAL FIX: Use the DATABASE_URL directly, assuming it now contains +psycopg2
    db_url_sync = settings.database_url 

    print(f"DEBUG: Initializing SYNCHRONOUS Engine for DB: {db_url_sync.split('@')[-1]}")
    
    try:
        # Create a standard synchronous engine
        engine = create_engine(
            db_url_sync,
            echo=False, 
            # Note: connect_args is generally not needed if sslmode is in the URL, 
            # but we keep it minimal here.
        )
        # Verify connection immediately
        with engine.connect():
            print("✅ SYNCHRONOUS DB connection successful.")
        
        return engine
        
    except Exception as e:
        print(f"❌ FATAL: Synchronous DB Engine initialization failed. Error: {type(e).__name__}: {e}")
        raise

# --- Token Fetch Simulation (remains the same) ---

def simulate_token_fetch(engine: SyncEngine, user_id: int):
    """Simulates the core synchronous token retrieval query."""
    print(f"\nDEBUG: Attempting token fetch for user ID {user_id}")

    try:
        with Session(engine) as session:
            # We must use the ORM query since the user model is defined
            stmt = select(User.gdrive_refresh_token).where(User.id == user_id)
            token = session.scalar(stmt)
            
            if token:
                print(f"✅ SUCCESS: Token retrieved. Length: {len(token)} chars.")
            else:
                print("⚠️ SUCCESS: User found, but token is NULL (not yet synced).")
            
            # The session automatically rolls back here since we didn't commit anything

    except Exception as e:
        print("\n--- CRITICAL EXCEPTION DURING SYNCHRONOUS QUERY ---")
        print(f"❌ The query failed! Error: {type(e).__name__}: {e}")
        print("This indicates a fundamental SQLAlchemy/ORM conflict in the worker context.")
        raise


if __name__ == "__main__":
    
    try:
        # Step 1: Initialize the Synchronous Engine
        sync_engine = init_sync_db_engine()
        
        # Step 2: Run the Fetch Simulation
        simulate_token_fetch(sync_engine, user_id=1)
        
    except Exception as e:
        print(f"\nDEBUGGER ABORTED: {e}")
