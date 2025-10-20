#!/usr/bin/env python3
import redis.asyncio as redis
import structlog
import json
from typing import List, Dict, Any, Optional

# Use multi-level parent relative import for config
from ..config import get_settings

logger = structlog.get_logger()
settings = get_settings()

class HistoryService:
    """
    Manages chat history persistence in Redis for conversational context.
    The history is stored as a list of JSON objects.
    """
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        # Key format: 'chat_history:{session_id}'
        self.key_prefix = "chat_history:"
        self.max_history_length = 10  # Store last 10 messages (5 user, 5 assistant)
        self.history_ttl = 3600  # History expires after 1 hour (3600 seconds)

    def _get_key(self, session_id: str) -> str:
        """Generates the Redis key for a session."""
        return f"{self.key_prefix}{session_id}"

    async def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Retrieves the full conversation history for a session."""
        key = self._get_key(session_id)
        
        # Redis returns a list of JSON strings
        history_json_list = await self.redis.lrange(key, 0, -1)
        
        history = []
        for json_str in history_json_list:
            try:
                # Decode the JSON string back into a Python dictionary
                history.append(json.loads(json_str))
            except json.JSONDecodeError:
                logger.error("Failed to decode history item.", json_str=json_str)
                continue
                
        # Return history in chronological order (oldest first)
        return history

    async def add_message(self, session_id: str, role: str, content: str):
        """Adds a new message to the session history."""
        key = self._get_key(session_id)
        
        message = {
            "role": role,
            "content": content
        }
        message_json = json.dumps(message)
        
        # 1. Add the new message to the right (end of list)
        await self.redis.rpush(key, message_json)
        
        # 2. Trim the list to the maximum length (removes oldest messages from the left)
        await self.redis.ltrim(key, -self.max_history_length, -1)
        
        # 3. Reset the expiry time
        await self.redis.expire(key, self.history_ttl)
        
        logger.debug("Message added to history.", session_id=session_id, role=role, content=content[:50])

    async def clear_history(self, session_id: str):
        """Clears the history for a session."""
        key = self._get_key(session_id)
        await self.redis.delete(key)
        logger.info("Chat history cleared.", session_id=session_id)

    async def format_history_for_prompt(self, session_id: str) -> List[Dict[str, str]]:
        """Retrieves history and formats it for LLM chat messages (Gemini format)."""
        raw_history = await self.get_history(session_id)
        
        # Gemini API chat format expects role: 'user' or 'model'
        formatted_history = []
        for msg in raw_history:
            # Map internal 'assistant' role to Gemini's 'model' role
            role = 'model' if msg.get('role') == 'assistant' else msg.get('role', 'user')
            
            # Ensure only 'user' and 'model' roles are used
            if role in ['user', 'model']:
                formatted_history.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })
        
        return formatted_history
