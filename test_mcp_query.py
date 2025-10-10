#!/usr/bin/env python3
"""
Test the MCP query interface
"""

import requests
import json

def test_mcp_query(query_text):
    """Test the MCP query_documents tool"""

    # MCP tool call format
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "query_documents",
            "arguments": {
                "input": query_text
            }
        },
        "id": 1
    }

    try:
        response = requests.post(
            "http://localhost:8080",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Query: {query_text}")
            print(f"📋 Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "what is libsodium"
    test_mcp_query(query)