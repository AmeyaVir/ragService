#!/usr/bin/env python3
import asyncio
from typing import Dict, Any, Optional, List
import google.generativeai as genai
import structlog
import json
import re 

# CORRECTED: Use parent-level import (..) to find config.py
from ..config import get_settings 

logger = structlog.get_logger()
settings = get_settings()


# --- Function Definition for Gemini ---
ARTIFACT_FUNCTION_SCHEMA = {
    "name": "generate_project_artifact",
    "description": "Generates a structured Project Management artifact (Excel Risk Register, Word Status Report, or PowerPoint Executive Pitch) based on the user's request and project context.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "artifact_type": {
                "type": "STRING",
                "description": "The type of artifact to generate. Must be one of: 'excel_risk_register', 'word_status_report', 'pptx_executive_pitch'."
            },
            "project_name": {
                "type": "STRING",
                "description": "The name of the currently selected project (e.g., 'Stone Hill Spud Prediction')."
            },
            "summary_content": {
                "type": "STRING",
                "description": "A brief, 2-3 sentence summary of the artifact's core content, derived from the user's query and RAG context."
            }
        },
        "required": ["artifact_type", "project_name", "summary_content"]
    }
}
# --------------------------------------


class LLMService:
    """
    Handles interactions with the Gemini LLM, including response generation
    and query classification.
    """
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        self.generation_config = {
            'temperature': 0.1,
            'top_p': 0.9,
            'top_k': 40,
            'max_output_tokens': 2048,
        }
        
        self.tools = [ARTIFACT_FUNCTION_SCHEMA]


    async def generate_response(self, prompt: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generates a text response from the LLM, potentially involving function calls.
        
        Returns:
            Dict: {'text': str, 'function_call': Optional[Dict]}
        """
        
        full_contents = history if history is not None else []
        # FIX: Removed the erroneous backslash. Python now sees a correct dictionary definition.
        full_contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        try:
            # Placeholder Logic: Detect keywords that imply artifact generation
            if re.search(r'generate|create|draft|export|excel|word|pptx|report|log|pitch', prompt.lower()):
                artifact_type = None
                if 'excel' in prompt.lower() or 'risk log' in prompt.lower():
                    artifact_type = 'excel_risk_register'
                elif 'word' in prompt.lower() or 'status report' in prompt.lower():
                    artifact_type = 'word_status_report'
                elif 'pptx' in prompt.lower() or 'executive pitch' in prompt.lower():
                    artifact_type = 'pptx_executive_pitch'
                
                if artifact_type:
                    # Mock the function call result
                    function_call_mock = {
                        "name": "generate_project_artifact",
                        "args": {
                            "artifact_type": artifact_type,
                            "project_name": "Stone Hill Spud Prediction", 
                            "summary_content": f"Drafting the artifact based on the current context and the request: '{prompt[:50]}...'"
                        }
                    }
                    return {"text": None, "function_call": function_call_mock}


            # Normal generation call (wrapped in a thread)
            response = await asyncio.to_thread(
                self.model.generate_content,
                contents=full_contents,
                generation_config=self.generation_config,
                tools=self.tools # Passed to enable function calling
            )
            
            # The LLM API response text is returned, or None if it failed/was blocked
            return {"text": response.text, "function_call": None}

        except Exception as e:
            logger.error("Failed to generate response/handle function call.", error=str(e))
            return {"text": "I apologize, but I encountered a service error while trying to process your request.", "function_call": None}


    async def classify_query_intent(self, query: str) -> Dict[str, Any]:
        """Classifies the user query's intent using the LLM."""
        classification_prompt = f"""
        Classify the following query into categories and determine if it requires a microsite/dashboard or an explicit structured artifact (Excel/Word/PPTX) response.

        Query: "{query}"

        Categories:
        - project_overview: Questions about project summaries, objectives
        - kpi_metrics: Questions about KPIs, metrics, performance data
        - value_outcomes: Questions about business value, ROI
        - microsite_request: Explicit request to generate a dashboard/microsite.
        - artifact_request: Explicit request to generate a structured document (e.g., 'risk log', 'status report', 'pitch deck').

        Respond *only* with a single JSON object in this exact format: {{\"primary_intent\": \"category\", \"requires_microsite\": true/false, \"requires_artifact\": true/false}}
        """

        try:
            response_data = await self.generate_response(prompt=classification_prompt)
            response_json_string = response_data['text']

            # Defensive Check: Ensure response_json_string is not None
            if not response_json_string:
                logger.warning("LLM response for intent classification was empty.")
                return {"primary_intent": "general_inquiry", "requires_microsite": False, "requires_artifact": False}

            # Safely attempt to parse the JSON string response
            try:
                start = response_json_string.find('{')
                end = response_json_string.rfind('}')
                if start != -1 and end != -1:
                    clean_json_string = response_json_string[start:end+1]
                else:
                    clean_json_string = response_json_string
                    
                result = json.loads(clean_json_string)
                # Ensure boolean types
                if 'requires_microsite' in result and isinstance(result['requires_microsite'], str):
                    result['requires_microsite'] = result['requires_microsite'].lower() == 'true'
                if 'requires_artifact' in result and isinstance(result['requires_artifact'], str):
                    result['requires_artifact'] = result['requires_artifact'].lower() == 'true'
                
                return result
            except json.JSONDecodeError:
                logger.warning("Failed to decode intent classification JSON. Defaulting intent.", response=response_json_string)
                return {"primary_intent": "general_inquiry", "requires_microsite": False, "requires_artifact": False}
        except Exception as e:
            logger.error("Failed to classify query intent.", error=str(e))
            return {"primary_intent": "general_inquiry", "requires_microsite": False, "requires_artifact": False}
