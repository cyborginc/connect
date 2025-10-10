# S3 to CyborgDB Pipeline with Red Panda Connect

Simple pipeline that reads documents from S3, generates embeddings with OpenAI, and stores them in CyborgDB.

## Setup

1. **Add your API keys to `.env`:**
   ```bash
   nano .env
   ```
   - `OPENAI_API_KEY`: Get from https://platform.openai.com/api-keys
   - `CYBORGDB_API_KEY`: Your CyborgDB API key

2. **Run the pipeline:**
   ```bash
   ./run_mcp_cyborgdb.sh
   ```

## Configuration

The pipeline uses:
- **Input**: AWS S3 bucket (`cyborgdb-mcp-demo`)
- **Processing**: OpenAI embeddings (text-embedding-ada-002)
- **Output**: CyborgDB encrypted vector storage

## Files

- `config/s3_to_cyborgdb_http.yaml` - Main pipeline configuration
- `.env` - Environment variables (credentials)
- `run_mcp_cyborgdb.sh` - Interactive run script

## Running Options

1. **MCP Server mode**: Runs on port 8080 for AI assistant integration
2. **Direct execution**: Processes files immediately

The pipeline will:
1. Scan your S3 bucket for documents
2. Generate embeddings via OpenAI API
3. Store vectors in CyborgDB with encryption