#!/usr/bin/env python3
"""
Simple MCP Server - Just implements query_documents tool
"""

import json
import requests
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import uuid

# Configuration
PROXY_PORT = 8083
NGROK_URL = "https://YOUR-NGROK-URL.ngrok.app"

# Load environment variables
def load_env():
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    except FileNotFoundError:
        print("Warning: .env file not found")
    return env_vars

ENV_VARS = load_env()

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

def generate_embedding(query: str) -> list:
    """Generate embedding for query using OpenAI"""
    response = requests.post(
        'https://api.openai.com/v1/embeddings',
        headers={
            'Authorization': f'Bearer {ENV_VARS["OPENAI_API_KEY"]}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'text-embedding-ada-002',
            'input': query
        }
    )
    response.raise_for_status()
    return response.json()['data'][0]['embedding']

def search_cyborgdb(query_vector: list) -> dict:
    """Search CyborgDB with query vector"""
    # Convert base64 key to hex if needed
    index_key = ENV_VARS['CYBORGDB_INDEX_KEY']
    if '=' in index_key or '+' in index_key or '/' in index_key:
        index_key_bytes = base64.b64decode(index_key)
        index_key_hex = index_key_bytes.hex()
    else:
        index_key_hex = index_key

    response = requests.post(
        f"{ENV_VARS['CYBORGDB_HOST']}/v1/vectors/query",
        headers={
            'X-API-Key': ENV_VARS['CYBORGDB_API_KEY'],
            'Content-Type': 'application/json'
        },
        json={
            'index_name': ENV_VARS.get('CYBORGDB_INDEX_NAME', 'documents'),
            'index_key': index_key_hex,
            'query_vectors': query_vector,
            'top_k': 5,
            'include': ['distance', 'metadata']
        }
    )

    if response.status_code == 200:
        return response.json()
    else:
        return {'error': f"CyborgDB returned {response.status_code}: {response.text}"}

def handle_query_documents(params: dict) -> dict:
    """Handle the query_documents tool call"""
    try:
        query_text = params.get('input', '')
        if not query_text:
            return {
                "error": {"code": -32602, "message": "Missing required parameter: input"}
            }

        print(f"🔍 Query: {query_text}")

        # Generate embedding
        print("📊 Generating embedding...")
        query_vector = generate_embedding(query_text)
        print(f"✅ Embedding generated ({len(query_vector)} dimensions)")

        # Search CyborgDB
        print("🔎 Searching CyborgDB...")
        results = search_cyborgdb(query_vector)

        if 'error' in results:
            return {"error": {"code": -32603, "message": results['error']}}

        # Format response
        if 'results' in results and results['results']:
            formatted_results = {
                "query": query_text,
                "found": len(results['results']),
                "documents": []
            }

            for result in results['results']:
                metadata = result.get('metadata', {})
                content = metadata.get('content', metadata.get('content_preview', ''))
                formatted_results["documents"].append({
                    "file": metadata.get('path', 'unknown'),
                    "score": result.get('distance', 0),
                    "bucket": metadata.get('bucket', ''),
                    "content": content if content else "No content stored - document needs re-indexing",
                    "preview": content[:500] if content else "No content"
                })

            return formatted_results
        else:
            return {
                "query": query_text,
                "found": 0,
                "documents": [],
                "message": "No matching documents found"
            }

    except Exception as e:
        print(f"❌ Error in query_documents: {e}")
        return {"error": {"code": -32603, "message": str(e)}}

class SimpleMCPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/manifest.json']:
            # Serve manifest
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(MANIFEST, indent=2).encode())

        elif self.path == '/sse':
            # Serve fake SSE endpoint
            session_id = str(uuid.uuid4())
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # Send the endpoint event
            self.wfile.write(b'event: endpoint\n')
            self.wfile.write(f'data: /messages?sessionId={session_id}\n\n'.encode())
            self.wfile.flush()

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith('/messages') or self.path in ['/', '/manifest.json']:
            # Handle JSON-RPC requests
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                rpc_request = json.loads(post_data.decode('utf-8'))
                print(f"📨 RPC Request: {rpc_request['method']}")

                response = {
                    "jsonrpc": "2.0",
                    "id": rpc_request.get("id")
                }

                if rpc_request.get("method") == "initialize":
                    response["result"] = {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "CyborgDB Query Server",
                            "version": "1.0.0"
                        }
                    }

                elif rpc_request.get("method") == "tools/list":
                    response["result"] = {
                        "tools": MANIFEST["tools"]
                    }

                elif rpc_request.get("method") == "tools/call":
                    tool_name = rpc_request.get("params", {}).get("name")
                    if tool_name == "query_documents":
                        tool_params = rpc_request.get("params", {}).get("arguments", {})
                        result = handle_query_documents(tool_params)

                        if "error" in result:
                            response["error"] = result["error"]
                        else:
                            response["result"] = {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
                    else:
                        response["error"] = {"code": -32601, "message": f"Unknown tool: {tool_name}"}

                else:
                    response["error"] = {"code": -32601, "message": f"Unknown method: {rpc_request.get('method')}"}

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            except Exception as e:
                print(f"❌ Error handling request: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())

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

def run_server(port=8081):
    server = HTTPServer(('0.0.0.0', port), SimpleMCPHandler)
    print(f"🚀 Simple MCP Server running on port {port}")
    print(f"📋 Manifest: {NGROK_URL}/manifest.json")
    print(f"🔧 Tools: query_documents")
    server.serve_forever()

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        NGROK_URL = sys.argv[1]
        MANIFEST["endpoints"]["sse"] = f"{NGROK_URL}/sse"
        MANIFEST["endpoints"]["messages"] = f"{NGROK_URL}/messages"

    run_server(PROXY_PORT)