#!/usr/bin/env python3
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from sqlalchemy import text
from redis.asyncio import Redis 

# CRITICAL FIX: Changed absolute imports to relative imports
from .config import get_settings
# Import the new function to get the engine
from .database import init_db, get_db_session, get_initialized_engine 
from .services.auth_service import AuthService
from .services.agent_orchestrator import AgentOrchestrator
from .services.history_service import HistoryService # NEW
from .services.artifact_service import ArtifactService # NEW
# NEW: artifacts route import
from .api.routes import auth, chat, projects, microsite, admin, artifacts 
from .celery_app import celery_app 

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
settings = get_settings()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self, history_service: HistoryService):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        self.history_service = history_service

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.user_sessions[session_id] = {"user_id": user_id}

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        self.user_sessions.pop(session_id, None)

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)

manager: ConnectionManager 

# Dependency Injection Helpers (Needed for local function dependency injection)
def get_artifact_service() -> ArtifactService:
    # Access artifact service from app state
    return app.state.artifact_service

def get_agent_orchestrator() -> AgentOrchestrator:
    # Access agent orchestrator from app state
    return app.state.agent_orchestrator

def get_connection_manager() -> ConnectionManager:
    # Access the manager instance from app state
    return app.state.manager
# ------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Analytics RAG Platform")
    await init_db()
    
    app.state.db_engine = get_initialized_engine()
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    
    # NEW: Initialize services
    app.state.history_service = HistoryService(app.state.redis)
    app.state.artifact_service = ArtifactService()
    
    # Initialize connection manager and agent orchestrator with dependencies
    global manager
    manager = ConnectionManager(app.state.history_service)
    app.state.manager = manager # CRITICAL FIX: Attach manager to app state
    app.state.agent_orchestrator = AgentOrchestrator(app.state.history_service)
    
    app.state.auth_service = AuthService()
    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down")
    await app.state.db_engine.dispose()
    await app.state.redis.close()


# Create FastAPI application
app = FastAPI(
    title="Analytics RAG Platform",
    description="Enterprise RAG system for analytics companies",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(microsite.router, prefix="/api/v1/microsite", tags=["Microsite"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Administration"])
app.include_router(artifacts.router, prefix="/api/v1/artifacts", tags=["Artifact Generation"])


@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Analytics RAG Platform",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    try:
        async with app.state.db_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            
        await app.state.redis.ping()

        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected"
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    user_id = "1"

    await manager.connect(websocket, session_id, user_id)

    try:
        while True:
            data = await websocket.receive_json()

            # Process message through agent orchestrator
            orchestrator = get_agent_orchestrator() 
            response = await orchestrator.process_message(
                user_id=user_id,
                session_id=session_id,
                message=data["message"],
                project_context=data.get("project_context", {}),
                message_type=data.get("type", "chat")
            )

            # Only send the standard 'response'/'error' message back here
            # 'artifact_generated' messages are sent directly from the artifacts endpoint via manager
            if response.get("type") in ["response", "error"]:
                await manager.send_message(session_id, response)

    except WebSocketDisconnect:
        manager.disconnect(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
