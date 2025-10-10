#!/usr/bin/env python3
"""
Test the MCP flow with RedPanda Connect
"""

import requests
import json

def test_mcp_flow():
    """Test the full MCP flow"""

    print("Testing MCP Server Flow")
    print("=" * 50)

    # Test 1: Get SSE endpoint
    print("1. Testing SSE endpoint...")
    try:
        response = requests.get("http://localhost:8082/sse", timeout=2)
        print(f"   SSE Status: {response.status_code}")
        if response.status_code == 200:
            # Read first few lines
            lines = response.text.split('\n')[:5]
            for line in lines:
                if line.strip():
                    print(f"   {line}")
    except Exception as e:
        print(f"   SSE Error: {e}")

    # Test 2: Try direct JSON-RPC to /message
    print("\n2. Testing direct JSON-RPC to /message...")
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0.0",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0"}
            },
            "id": 1
        }

        response = requests.post(
            "http://localhost:8082/message",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )

        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

    except Exception as e:
        print(f"   Error: {e}")

    # Test 3: Test through proxy
    print("\n3. Testing through proxy...")
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }

        response = requests.post(
            "http://localhost:8081/",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )

        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_mcp_flow()