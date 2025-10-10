#!/usr/bin/env python3
"""
Simple test to understand RedPanda Connect MCP flow
"""

import requests
import json

def test_direct_flow():
    """Test the direct flow with RedPanda Connect"""

    print("Testing RedPanda Connect MCP Server Flow")
    print("=" * 50)

    # Step 1: Connect to SSE and get session ID
    print("1. Connecting to SSE...")
    session_id = None

    try:
        sse_response = requests.get("http://localhost:8082/sse", stream=True)

        for line in sse_response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                print(f"   SSE: {line_str}")

                if line_str.startswith('data: /message?sessionId='):
                    session_id = line_str.split('sessionId=')[1]
                    print(f"   ✅ Got session ID: {session_id}")
                    break

        if not session_id:
            print("   ❌ No session ID found")
            return

        # Step 2: Make JSON-RPC request using the session ID
        print("\n2. Making JSON-RPC request...")

        json_rpc_payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }

        # Try the request with the session ID
        url = f"http://localhost:8082/message?sessionId={session_id}"
        print(f"   URL: {url}")
        print(f"   Payload: {json.dumps(json_rpc_payload)}")

        json_response = requests.post(
            url,
            json=json_rpc_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        print(f"   Status: {json_response.status_code}")
        print(f"   Response: {json_response.text}")

        # Keep the SSE connection open while making the JSON-RPC request
        # This is probably what RedPanda Connect expects
        sse_response.close()

    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_direct_flow()