#!/usr/bin/env python3
import asyncio
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import structlog
from qdrant_client.http.exceptions import UnexpectedResponse

# CORRECTED: Use parent-level import (..) to find config.py
from ..config import get_settings
# CORRECTED: Use relative imports for sibling services
from .llm_service import LLMService
from .qdrant_service import QdrantService 

logger = structlog.get_logger()
settings = get_settings()


class RAGService:
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.llm_service = LLMService()
        self.qdrant_service = QdrantService()

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a list of text strings."""
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True).tolist()
        return embeddings

    async def index_document_chunks(self, augmented_chunks: List[Dict[str, Any]]):
        if not augmented_chunks:
            logger.warning("No chunks provided for indexing.")
            return

        texts = [chunk['content'] for chunk in augmented_chunks]
        embeddings = await asyncio.to_thread(self.create_embeddings, texts)
        
        if len(embeddings) != len(augmented_chunks):
            logger.error("Embedding count mismatch with chunk count. Aborting index.")
            return

        points_data = []
        logger.info("Preparing points for Qdrant indexing.", count=len(augmented_chunks))
        
        for i, chunk in enumerate(augmented_chunks):
            payload = chunk.copy() 
            
            points_data.append({
                "vector": embeddings[i],
                "payload": payload 
            })

        try:
            await self.qdrant_service.index_points(points_data)
            logger.info("Batch indexing complete.", count=len(points_data))
        except UnexpectedResponse as e:
            logger.error("Qdrant indexing failed due to unexpected response.", error=str(e))
            raise 
        except Exception as e:
            logger.error("General error during Qdrant indexing.", error=str(e))
            raise 


    async def retrieve_context(self, query: str, tenant_id: str, project_ids: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        
        # CRITICAL FIX: Standardize tenant_id to the expected indexed value ('1')
        standardized_tenant_id = "1" if tenant_id == "demo" else tenant_id
        
        query_embedding_list = await asyncio.to_thread(self.create_embeddings, [query])
        query_embedding = query_embedding_list[0]

        retrieved_results = await self.qdrant_service.search_vectors(\
            query_embedding=query_embedding,\
            project_ids=project_ids,\
            tenant_id=standardized_tenant_id,\
            limit=limit\
        )

        context = []
        for result in retrieved_results:
            payload = result['payload']
            context.append({
                "content": payload.get('content', 'Content not available.').strip(),
                "score": result.get('score', 0.0),
                "source_file": payload.get('source_file', 'Unknown File'),
                "project_id": payload.get('project_id', 'Unknown Project'),
                "document_id": payload.get('document_id', 'Unknown Doc'),
                "context_type": "document_chunk"
            })
            
        logger.info("Context retrieved.", query=query, retrieved_count=len(context))
        return context


    async def generate_response(self, query: str, context: List[Dict[str, Any]], history: List[Dict[str, Any]], project_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generates a final answer using the LLM based on the query, retrieved context, and chat history.
        """
        context_text = "\n\n".join([f"[{ctx['source_file']}/{ctx['project_id']}] {ctx['content']}" for ctx in context])
        
        has_context = bool(context_text.strip())
        
        # Format RAG context for the prompt
        rag_context_section = f"CONTEXT: {context_text if has_context else 'NO_RAG_CONTEXT_AVAILABLE'}"
        
        # Format chat history for the prompt (as a summary for grounding)
        history_summary_parts = []
        for msg in history:
            role = msg.get('role', 'user')
            # Extract content from Gemini API format parts
            content = msg.get('parts', [{}])[0].get('text', '')
            history_summary_parts.append(f"{role.upper()}: {content}")
        history_summary = "\n".join(history_summary_parts)
        
        prompt = f"""
        You are an expert financial and technical analyst for the "Analytics RAG Platform" specializing in the oil and gas sector.
        
        Your primary goal is to provide a helpful, structured response to the user's question, **while respecting the conversation history**.

        ---
        CONVERSATION_HISTORY: {history_summary if history_summary else "No previous conversation."}
        
        {rag_context_section}
        
        Question: {query}
        ---

        INSTRUCTION:
        1. **Contextualize**: Use the **CONVERSATION_HISTORY** to understand the user's intent. 
        2. **Citation & Grounding**: If CONTEXT is available, you **MUST** use the facts and terminology found in it. Any direct reference to project-specific data (e.g., spud activity predictions) from the CONTEXT **MUST** be immediately followed by a citation in the format [file/project].
        3. **Constraint**: Do not mention that you have or lack context. Do not include the CONTEXT text in your final answer.
        4. **Function Call**: Do NOT try to output a function call result here. If a function call is needed, the `LLMService` will handle it before this prompt is executed.
        
        Your Answer (Format the response professionally, e.g., using markdown lists/headings):
        """
        
        # Pass the full history (in Gemini format) for the actual API call
        response_data = await self.llm_service.generate_response(prompt, history=history)
        
        # CRITICAL FIX: Ensure the keys are safely retrieved, as response_data might be minimal during a function call
        response_text = response_data.get('text', '') # Defaults to empty string if LLM returns None (e.g. for function call)
        function_call = response_data.get('function_call')

        sources_list = []
        unique_sources = set()
        for ctx in context:
            source_tuple = (ctx["source_file"], ctx["project_id"])
            if source_tuple not in unique_sources:
                unique_sources.add(source_tuple)
                sources_list.append({
                    "file": ctx["source_file"], 
                    "project": ctx["project_id"], 
                    "type": ctx["context_type"],
                    "score": ctx["score"]
                })

        return {
            "response": response_text,
            "sources": sources_list,
            "context_used": len(context),
            "function_call": function_call
        }
