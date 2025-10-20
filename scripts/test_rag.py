#!/usr/bin/env python3
"""
Test script for RAG functionality
"""
import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.rag_service import RAGService
from services.llm_service import LLMService

async def test_rag_system():
    """Test the RAG system with sample data"""
    print("Testing RAG system...")

    try:
        # Initialize services
        rag_service = RAGService()
        llm_service = LLMService()

        # Test LLM service
        print("\n1. Testing LLM service...")
        response = await llm_service.generate_response("Hello, how are you?")
        print(f"LLM Response: {response[:100]}...")

        # Test query classification
        print("\n2. Testing query classification...")
        intent = await llm_service.classify_query_intent("What are the KPIs for our projects?")
        print(f"Intent: {intent}")

        # Test RAG retrieval (with empty store)
        print("\n3. Testing RAG retrieval...")
        context = await rag_service.retrieve_context(
            query="production efficiency",
            tenant_id="demo",
            project_ids=["demo_project"],
            limit=5
        )
        print(f"Retrieved {len(context)} context items")

        # Test response generation
        print("\n4. Testing response generation...")
        response_data = await rag_service.generate_response(
            query="What are our key performance indicators?",
            context=context
        )
        print(f"Generated response: {response_data['response'][:200]}...")

        print("\n✅ RAG system test completed successfully!")

    except Exception as e:
        print(f"❌ RAG system test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_rag_system())
