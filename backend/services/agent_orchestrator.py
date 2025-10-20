#!/usr/bin/env python3
import asyncio
from typing import Dict, Any, List
import structlog
import httpx 
from fastapi import Depends

# CORRECTED: Use relative imports for modules within the 'backend' package
from .rag_service import RAGService
from .llm_service import LLMService
from .gdrive_service import GoogleDriveService 
from .history_service import HistoryService
# Import ArtifactService for type hinting
from .artifact_service import ArtifactService 

logger = structlog.get_logger()

# Constants for project name mapping
PROJECT_ID_TO_NAME = {
    "1": "MARS Analytics Platform", 
    "6": "Stone Hill Spud Prediction" # Mocking the project ID for the user's use case
}
DEFAULT_PROJECT_NAME = "Analytics Project"


class AgentOrchestrator:
    def __init__(self, history_service: HistoryService):
        self.rag_service = RAGService()
        self.llm_service = LLMService()
        self.history_service = history_service
        # Use httpx for internal service calls (e.g., to the local artifacts endpoint)
        self.http_client = httpx.AsyncClient(base_url="http://localhost:8000") 


    async def process_message(self, user_id: str, session_id: str, message: str, project_context: Dict[str, Any], message_type: str = "chat") -> Dict[str, Any]:
        
        # 0. Add user message to history immediately
        await self.history_service.add_message(session_id, "user", message)
        
        try:
            # 1. Get current conversation history for LLM grounding
            history = await self.history_service.format_history_for_prompt(session_id)
            
            # 2. Get project details
            tenant_id = project_context.get("tenant_id", "demo")
            project_ids = project_context.get("project_ids", [])
            selected_project_id = project_ids[0] if project_ids else None
            project_name = PROJECT_ID_TO_NAME.get(selected_project_id, DEFAULT_PROJECT_NAME)

            # 3. Retrieve context using RAG
            context = await self.rag_service.retrieve_context(\
                query=message,\
                tenant_id=tenant_id,\
                project_ids=project_ids,\
                limit=5\
            )

            # 4. Generate initial response (triggers LLM to decide on text vs function call)
            response_data = await self.rag_service.generate_response(\
                query=message,\
                context=context,\
                history=history,\
                project_context=project_context\
            )
            
            response_text = response_data["response"]
            
            # CRITICAL FIX: Safely access function_call. If it's None, this defaults to None.
            function_call = response_data.get("function_call")

            # --- 5. Function Call Handling ---
            if function_call and function_call.get("name") == "generate_project_artifact":
                
                args = function_call.get("args", {})
                artifact_type = args.get("artifact_type")
                
                logger.info("Handling function call to generate artifact.", type=artifact_type)
                
                # Internal API call to the new artifact route
                artifact_api_payload = {
                    "artifact_type": artifact_type,
                    "project_name": project_name,
                    "session_id": session_id,
                    # Pass the LLM's generated summary and mock data to fill the artifact
                    "data": {"summary": args.get("summary_content")}
                }
                
                try:
                    # Calls the local API endpoint which executes file generation and WS messaging
                    api_response = await self.http_client.post("/api/v1/artifacts/generate", json=artifact_api_payload)
                    api_response.raise_for_status()
                    
                    # LLM's original text response is the final text message to the user
                    final_response_text = response_text
                    
                except httpx.HTTPStatusError as e:
                    logger.error("Internal artifact generation failed via API.", error=str(e), status=e.response.status_code)
                    final_response_text = f"I failed to generate the requested artifact ({artifact_type.replace('_', ' ')}) due to an internal system error."
                
                except Exception as e:
                    logger.error("Unexpected error during artifact generation call.", error=str(e))
                    final_response_text = "I encountered an error while trying to generate the artifact."

            else:
                # Normal chat response
                final_response_text = response_text
            
            # 6. Add assistant response to history
            await self.history_service.add_message(session_id, "assistant", final_response_text)
            
            # 7. Return the final structured response (without artifact data, which is sent via separate WS message)
            return {
                "type": "response",
                "session_id": session_id,
                "response": final_response_text,
                "sources": response_data["sources"],
                # Fix: Need to ensure intent is generated (or defaulted) to prevent KeyError upstream
                "intent": response_data.get("intent", {"primary_intent": "chat"}), 
                "context_used": response_data["context_used"],
                "timestamp": asyncio.get_event_loop().time()
            }

        except Exception as e:
            error_message = f"I encountered an error processing your request: {type(e).__name__}. This may be related to LLM connectivity or history processing."
            await self.history_service.add_message(session_id, "assistant", error_message)
            
            logger.error("Failed to process message in orchestrator", error=str(e))
            return {
                "type": "error",
                "session_id": session_id,
                "error": error_message,
                "timestamp": asyncio.get_event_loop().time()
            }
