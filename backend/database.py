#!/usr/bin/env python3
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, MetaData
from sqlalchemy.sql import func
import structlog
import re

from .config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Database engine and session
engine: Optional[AsyncEngine] = None
SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None

class Base(DeclarativeBase):
    metadata = MetaData()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Minimal User Model
class User(Base):
    __tablename__ = "users"

    # Existing fields
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # NEW: Fields for Google Drive OAuth token
    gdrive_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gdrive_linked_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)


async def init_db():
    global engine, SessionLocal

    # CRITICAL FIX: Ensure the URL uses the async driver (asyncpg) and the correct SSL parameter ('ssl').
    # 1. Strip all potential driver prefixes and use the base postgresql:// prefix.
    # 2. Add the explicit +asyncpg driver name.
    # 3. Swap the synchronous parameter 'sslmode' (from .env) to the asynchronous parameter 'ssl'.
    
    url_base = re.sub(r"postgresql(\+\w+)?:", "postgresql:", settings.database_url)
    
    # Ensure the URL is clean before swapping
    async_db_url = url_base.replace("postgresql://", "postgresql+asyncpg://", 1)
    async_db_url = async_db_url.replace("sslmode=", "ssl=", 1) # Swap parameter name for asyncpg compatibility

    engine = create_async_engine(
        async_db_url,
        echo=settings.environment == "development",
        pool_size=20,
        max_overflow=30
    )

    SessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Validation attempt
    async with engine.begin() as conn:
        await conn.execute(func.now()) 
    logger.info("Database engine initialized and connection validated.")

def get_initialized_engine() -> AsyncEngine:
    if engine is None:
        raise RuntimeError("Database engine has not been initialized.")
    return engine


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    if not SessionLocal:
        logger.error("Attempted to get DB session before initialization succeeded.")
        raise RuntimeError("Database not initialized")

    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_db_session() as session:
        yield session
