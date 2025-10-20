#!/usr/bin/env python3
"""
Standalone script to debug a specific database commit failure.
It simulates the token update logic to expose a hidden SQLAlchemy/asyncpg exception.
"""
import os
import sys
import asyncio
import structlog
from datetime import datetime

# --- Path and Configuration Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import the necessary backend components
from backend.database import init_db, get_db_session, User
from sqlalchemy import update, select # CRITICAL FIX: Added 'select' import
from sqlalchemy.sql import func
from backend.config import get_settings

# --- Setup ---
logger = structlog.get_logger()
settings = get_settings()

async def simulate_token_save():
    print("--- Starting Database Commit Debugger ---")
    print(f"DB URL: {settings.database_url.split('@')[-1]}")
    
    # 1. Initialize DB Engine (where the fatal connection error usually happens)
    try:
        await init_db()
        print("✅ DB Engine Initialized and connection validated.")
    except Exception as e:
        print(f"❌ FATAL: DB Engine initialization failed. Error: {e}")
        # Print full trace for fatal connection error
        import traceback
        traceback.print_exc(file=sys.stdout)
        return

    # 2. Simulate the Token Data
    user_id = 1
    # Use a dummy token string that is the correct data type (Text/str)
    DUMMY_TOKEN = f"DEBUG_TOKEN_{datetime.now().isoformat()}"
    
    print(f"\nAttempting to save dummy token to user ID: {user_id}")
    
    # 3. Simulate the Transaction and Commit (The exact code that is failing live)
    try:
        async with get_db_session() as db:
            # We must first ensure the user exists for the UPDATE to work
            # FIX: 'select' is now defined and the query will execute
            if await db.scalar(select(User.id).where(User.id == user_id)) is None:
                print(f"❌ FATAL: User ID {user_id} not found. Rerun init_db.py!")
                return
            
            # Execute the update statement from auth.py
            stmt = update(User).where(User.id == user_id).values(
                gdrive_refresh_token=DUMMY_TOKEN,
                gdrive_linked_at=func.now()
            )
            await db.execute(stmt)
            await db.commit() # THIS IS THE LINE THAT FAILS LIVE

        print(f"\n✅ SUCCESS! Database commit completed for User ID {user_id}.")
        print(f"Token saved: {DUMMY_TOKEN}. Please verify in psql.")

    except Exception as e:
        print("\n--- CRITICAL EXCEPTION DURING DB COMMIT ---")
        print(f"❌ The transaction failed! Error: {e}")
        import traceback
        traceback.print_exc(file=sys.stdout)
        print("------------------------------------------")


if __name__ == "__main__":
    # Ensure this script is run from the project root.
    try:
        asyncio.run(simulate_token_save())
    except RuntimeError as e:
        print(f"Runtime Error: {e}. Ensure no other asyncio loop is running.")
