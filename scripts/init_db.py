#!/usr/bin/env python3
"""
Database initialization script for Analytics RAG Platform
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
print(sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from database import init_db, get_db_session
from config import get_settings

# NEW: Import text for raw SQL execution
from sqlalchemy import text

async def main():
    """Initialize the database with tables and sample data"""
    print("Initializing Analytics RAG Platform database...")

    try:
        # Initialize database tables
        await init_db()
        print("✅ Database tables created successfully")
        
        # Load and execute init.sql contents
        script_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(script_dir, 'init.sql'), 'r') as f:
            sql_script = f.read()

        # Add sample data
        async with get_db_session() as db:
            # Execute the full script, which handles table creation and demo data insertion
            await db.execute(text(sql_script))
            await db.commit()
            print("✅ Sample data created successfully")

        print("Database initialization complete!")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
