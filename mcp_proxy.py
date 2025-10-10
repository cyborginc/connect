#!/usr/bin/env python3
"""
MCP Proxy Server - Serves manifest and proxies to RedPanda Connect MCP server
All endpoints on one port for ngrok
"""

import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

# Configuration
REDPANDA_MCP_PORT = 8082  # RedPanda Connect MCP server
PROXY_PORT = 8081  # This proxy server port
NGROK_URL = "https://YOUR-NGROK-URL.ngrok.app"  # Update this with your actual ngrok URL

# Store active sessions
active_sessions = {}

MANIFEST = {
    "name": "CyborgDB Query Server",
    "version": "1.0.0",
    "description": "Query your indexed documents in CyborgDB using semantic search",
    "transport": "sse",
    "endpoints": {
        "sse": f"{NGROK_URL}/sse",
        "messages": f"{NGROK_URL}/messages"
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
}

class MCPProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/manifest.json']:
            # Serve manifest at both root and /manifest.json
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(MANIFEST, indent=2).encode())

        elif self.path == '/sse':
            # Proxy SSE from RedPanda Connect and capture session ID
            try:
                response = requests.get(
                    f"http://localhost:{REDPANDA_MCP_PORT}/sse",
                    stream=True
                )

                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                session_id = None
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        self.wfile.write(line + b'\n')
                        self.wfile.flush()

                        # Extract session ID from the endpoint event
                        if line_str.startswith('data: /message?sessionId='):
                            session_id = line_str.split('sessionId=')[1]
                            client_ip = self.client_address[0]
                            active_sessions[client_ip] = session_id
                            print(f"Captured session ID {session_id} for client {client_ip}")

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith('/messages') or self.path in ['/', '/manifest.json']:
            # Handle JSON-RPC at multiple endpoints
            # Extract query parameters
            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)

            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                # Get session ID for this client
                client_ip = self.client_address[0]
                session_id = active_sessions.get(client_ip)

                if not session_id:
                    # Try to extract from existing query params first
                    if query_params.get('sessionId'):
                        session_id = query_params['sessionId'][0]
                    else:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "error": "No active session. Connect to /sse first."
                        }).encode())
                        return

                # Forward to RedPanda Connect /message endpoint with session ID
                url = f"http://localhost:{REDPANDA_MCP_PORT}/message?sessionId={session_id}"

                # Add any additional query parameters
                if query_params:
                    import urllib.parse
                    additional_params = {k: v for k, v in query_params.items() if k != 'sessionId'}
                    if additional_params:
                        url += "&" + urllib.parse.urlencode(additional_params, doseq=True)

                response = requests.post(
                    url,
                    data=post_data,
                    headers={'Content-Type': 'application/json'}
                )

                self.send_response(response.status_code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response.content)

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_proxy(port=8080):
    server = HTTPServer(('0.0.0.0', port), MCPProxyHandler)
    print(f"MCP Proxy running on port {port}")
    print(f"Endpoints:")
    print(f"  GET  /manifest.json - MCP manifest")
    print(f"  GET  /sse          - SSE stream (proxied)")
    print(f"  POST /messages     - JSON-RPC (proxied to /message)")
    server.serve_forever()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        NGROK_URL = sys.argv[1]
        # Update manifest with provided URL
        MANIFEST["endpoints"]["sse"] = f"{NGROK_URL}/sse"
        MANIFEST["endpoints"]["messages"] = f"{NGROK_URL}/messages"

    run_proxy(PROXY_PORT)