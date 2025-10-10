#!/usr/bin/env python3
"""
MCP Manifest Server - Wraps RedPanda Connect MCP server with a manifest endpoint
"""

import json
from flask import Flask, jsonify, request, Response
import requests
import threading
import time

app = Flask(__name__)

# Configuration
REDPANDA_MCP_HOST = "localhost"
REDPANDA_MCP_PORT = 8082
PUBLIC_URL = "http://23.22.29.11:8080"  # Change this to your public URL

@app.route('/manifest.json')
def manifest():
    """Serve the MCP manifest"""
    return jsonify({
        "name": "CyborgDB Query Server",
        "version": "1.0.0",
        "description": "Query your indexed documents in CyborgDB using semantic search",
        "transport": "sse",
        "endpoints": {
            "sse": f"{PUBLIC_URL}/sse",
            "message": f"{PUBLIC_URL}/message"
        },
        "tools": [
            {
                "name": "query_documents",
                "description": "Query your indexed documents in CyborgDB using semantic search",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "description": "The search query text"
                        }
                    },
                    "required": ["input"]
                }
            }
        ]
    })

@app.route('/sse')
def sse_endpoint():
    """Proxy SSE endpoint from RedPanda Connect"""
    def generate():
        # Connect to RedPanda MCP server's SSE endpoint
        response = requests.get(
            f"http://{REDPANDA_MCP_HOST}:{REDPANDA_MCP_PORT}/sse",
            stream=True
        )

        for line in response.iter_lines():
            if line:
                yield line.decode('utf-8') + '\n\n'

    return Response(generate(), mimetype='text/event-stream')

@app.route('/message', methods=['POST'])
def message_endpoint():
    """Proxy message endpoint to RedPanda Connect"""
    # Get session ID from query params
    session_id = request.args.get('sessionId')

    if not session_id:
        return jsonify({"error": "Missing sessionId"}), 400

    # Forward the request to RedPanda MCP server
    try:
        response = requests.post(
            f"http://{REDPANDA_MCP_HOST}:{REDPANDA_MCP_PORT}/message",
            params={"sessionId": session_id},
            json=request.json,
            headers={'Content-Type': 'application/json'}
        )

        return response.json(), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        PUBLIC_URL = sys.argv[1]

    print(f"Starting MCP Manifest Server...")
    print(f"Manifest URL: {PUBLIC_URL}/manifest.json")
    print(f"Proxying to RedPanda MCP at: {REDPANDA_MCP_HOST}:{REDPANDA_MCP_PORT}")

    # Run Flask server
    app.run(host='0.0.0.0', port=8083, threaded=True)