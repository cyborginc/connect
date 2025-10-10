#!/usr/bin/env python3
"""
Test MCP server tool discovery
"""

import requests
import json
import sys

def test_mcp_server(host="localhost", port=8082):
    """Test MCP server tool discovery"""

    # Try to list tools via JSON-RPC
    url = f"http://{host}:{port}"

    # Initialize the connection
    init_payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0.0",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        },
        "id": 1
    }

    # List tools
    list_tools_payload = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }

    print(f"Testing MCP server at {url}")
    print("-" * 50)

    # Test different endpoints
    endpoints = ["/", "/rpc", "/jsonrpc"]

    for endpoint in endpoints:
        try:
            print(f"\nTrying endpoint: {endpoint}")

            # Try initialize
            response = requests.post(
                url + endpoint,
                headers={"Content-Type": "application/json"},
                json=init_payload,
                timeout=2
            )
            print(f"  Initialize: {response.status_code}")
            if response.status_code == 200:
                print(f"  Response: {response.text[:200]}")

                # Try list tools
                response = requests.post(
                    url + endpoint,
                    headers={"Content-Type": "application/json"},
                    json=list_tools_payload,
                    timeout=2
                )
                print(f"  List tools: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "tools" in result["result"]:
                        tools = result["result"]["tools"]
                        print(f"  Found {len(tools)} tools:")
                        for tool in tools:
                            print(f"    - {tool.get('name', 'unknown')}: {tool.get('description', '')[:50]}")
                    else:
                        print(f"  Response: {response.text[:200]}")

        except Exception as e:
            print(f"  Error: {e}")

    # Also test SSE endpoint
    print("\n\nTesting SSE endpoint...")
    try:
        # SSE typically requires a GET request
        response = requests.get(
            url + "/sse",
            stream=True,
            timeout=2
        )
        print(f"SSE endpoint status: {response.status_code}")
        if response.status_code == 200:
            # Read first few lines
            for i, line in enumerate(response.iter_lines()):
                if i > 5:
                    break
                if line:
                    print(f"  {line.decode()}")
    except Exception as e:
        print(f"SSE Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
        test_mcp_server(port=port)
    else:
        test_mcp_server()