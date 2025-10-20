#!/usr/bin/env python3
"""
Standalone script to debug the WebSocket connection by acting as a client.
It connects to the FastAPI /ws endpoint, sends a complete RAG query payload,
and prints the server's raw response.
"""
import asyncio
import json
import websockets
import os
import sys

# --- Configuration ---
# Your FastAPI server should be running on localhost:8000
WS_URL = "ws://localhost:8000"
SESSION_ID = f"debug_session_{asyncio.get_event_loop().time()}"
ENDPOINT = f"{WS_URL}/ws/{SESSION_ID}"

# Based on your logs, the successful project/tenant IDs are "6" and "1"
PAYLOAD = {
    "message": "What is the primary analytical goal regarding reservoir characteristics and performance?",
    "project_context": {
        "tenant_id": "demo", # Use the slug for tenant consistency
        "project_ids": ["6"], # Use the confirmed numeric ID as string for Qdrant filter
        "selected_project": "Diatomite"
    },
    "type": "chat"
}

async def run_websocket_test():
    print(f"--- WebSocket RAG Client Debugger ---")
    print(f"Connecting to: {ENDPOINT}")
    print(f"Sending Payload: {PAYLOAD['message'][:50]}...")
    
    try:
        # Use websockets.connect to establish the connection
        async with websockets.connect(ENDPOINT) as websocket:
            print("✅ Connection established.")

            # 1. Send the message payload
            await websocket.send(json.dumps(PAYLOAD))
            print("INFO: Message sent. Waiting for server response...")

            # 2. Wait for the server's response
            response_json = await websocket.recv()
            response_data = json.loads(response_json)

            print("\n--- SERVER RESPONSE (JSON) ---")
            print(json.dumps(response_data, indent=4))
            print("------------------------------")
            
            # Check for success/failure
            if response_data.get("sources"):
                print("✅ RESULT: Context retrieval SUCCEEDED (Sources are present).")
            else:
                print("❌ RESULT: Context retrieval FAILED (No sources provided).")

    except ConnectionRefusedError:
        print("\n❌ ERROR: Connection refused. Ensure FastAPI is running at http://localhost:8000.")
    except websockets.exceptions.ConnectionClosedOK:
        print("\n⚠️ WARNING: Connection closed by server before receiving a full response.")
        print("This indicates a crash in the backend's WebSocket handler.")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(run_websocket_test())
    except Exception as e:
        print(f"FATAL SCRIPT ERROR: {e}")
