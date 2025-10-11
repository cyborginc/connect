#!/usr/bin/env python3
"""
Query your CyborgDB vector database
"""

import os
import sys
import json
import requests
import base64
from typing import List, Dict

# Load environment variables
def load_env():
    env_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                env_vars[key] = value
    return env_vars

def generate_embedding(query: str, api_key: str) -> List[float]:
    """Generate embedding for query using OpenAI"""
    response = requests.post(
        'https://api.openai.com/v1/embeddings',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'text-embedding-ada-002',
            'input': query
        }
    )
    response.raise_for_status()
    return response.json()['data'][0]['embedding']

def search_cyborgdb(query_vector: List[float], env_vars: Dict) -> Dict:
    """Search CyborgDB with query vector"""
    # Convert base64 key to hex
    index_key = env_vars['CYBORGDB_INDEX_KEY']
    if '=' in index_key or '+' in index_key or '/' in index_key:
        # It's base64, convert to hex
        index_key_bytes = base64.b64decode(index_key)
        index_key_hex = index_key_bytes.hex()
    else:
        index_key_hex = index_key

    response = requests.post(
        f"{env_vars['CYBORGDB_HOST']}/v1/vectors/query",
        headers={
            'X-API-Key': env_vars['CYBORGDB_API_KEY'],
            'Content-Type': 'application/json'
        },
        json={
            'index_name': env_vars.get('CYBORGDB_INDEX_NAME', 'documents'),
            'index_key': index_key_hex,
            'query_vectors': query_vector,  # Note: query_vectors not query_vector
            'top_k': 5,
            'include': ['distance', 'metadata']
        }
    )

    if response.status_code == 200:
        return response.json()
    else:
        return {'error': f"CyborgDB returned {response.status_code}: {response.text}"}

def main():
    # Load environment
    env_vars = load_env()

    # Get query from command line or interactive
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
    else:
        query = input("Enter your search query: ")

    print(f"\n🔍 Searching for: {query}")

    # Generate embedding
    print("📊 Generating embedding...")
    try:
        query_vector = generate_embedding(query, env_vars['OPENAI_API_KEY'])
        print(f"✅ Embedding generated ({len(query_vector)} dimensions)")
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return

    # Search CyborgDB
    print("🔎 Searching CyborgDB...")
    results = search_cyborgdb(query_vector, env_vars)

    if 'error' in results:
        print(f"❌ Error: {results['error']}")
    elif 'results' in results and results['results']:
        print(f"\n✅ Found {len(results['results'])} matching documents:\n")
        for i, result in enumerate(results['results'], 1):
            metadata = result.get('metadata', {})
            print(f"{i}. {metadata.get('path', 'Unknown file')}")
            print(f"   Score: {result.get('distance', 0):.4f}")

            # Show content preview
            content = metadata.get('content', metadata.get('content_preview', ''))
            if content:
                print(f"   Content Preview: {content[:300]}...")
            else:
                print(f"   Content: No content stored")
            print()
    else:
        print("📭 No matching documents found")

if __name__ == "__main__":
    main()