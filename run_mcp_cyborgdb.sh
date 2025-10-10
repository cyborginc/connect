#!/bin/bash

# Red Panda Connect MCP Server Runner for S3 to CyborgDB Pipeline
# This script runs the MCP server with S3 to CyborgDB configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Red Panda Connect - S3 to CyborgDB Pipeline${NC}"
echo "============================================"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found!${NC}"
    echo "Creating .env from template..."
    cat > .env << 'EOF'
# S3 Configuration
S3_BUCKET=your-s3-bucket-name
S3_PREFIX=documents/
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key

# OpenAI Configuration (for embeddings)
OPENAI_API_KEY=your-openai-api-key

# CyborgDB Configuration
CYBORGDB_HOST=api.cyborg.com
CYBORGDB_API_KEY=your-cyborgdb-api-key
CYBORGDB_INDEX_NAME=documents
CYBORGDB_INDEX_KEY=$(openssl rand -base64 32)
EOF
    echo -e "${GREEN}.env file created. Please edit it with your credentials.${NC}"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Validate required environment variables
required_vars=(
    "S3_BUCKET"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "OPENAI_API_KEY"
    "CYBORGDB_API_KEY"
    "CYBORGDB_INDEX_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ] || [ "${!var}" == "your-"* ]; then
        missing_vars+=($var)
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo -e "${RED}Error: Missing or invalid environment variables:${NC}"
    printf '%s\n' "${missing_vars[@]}"
    echo -e "${YELLOW}Please edit .env file and set all required values${NC}"
    exit 1
fi

# Build the binary if it doesn't exist
if [ ! -f "./redpanda-connect" ]; then
    echo -e "${YELLOW}Building Red Panda Connect...${NC}"
    go build -o redpanda-connect ./cmd/redpanda-connect
fi

# Display configuration
echo -e "${GREEN}Configuration:${NC}"
echo "  S3 Bucket: ${S3_BUCKET}"
echo "  S3 Prefix: ${S3_PREFIX:-/}"
echo "  AWS Region: ${AWS_REGION}"
echo "  CyborgDB Host: ${CYBORGDB_HOST}"
echo "  CyborgDB Index: ${CYBORGDB_INDEX_NAME}"
echo ""

# Ask user how to run
echo "How would you like to run the pipeline?"
echo "1) MCP Server mode (HTTP on port 8080)"
echo "2) Direct pipeline execution (process files now)"
echo "3) Exit"
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo -e "${GREEN}Starting MCP Server on port 8080...${NC}"
        ./redpanda-connect mcp-server --address :8080 --env-file .env config
        ;;
    2)
        echo -e "${GREEN}Running pipeline directly...${NC}"
        ./redpanda-connect --env-file .env --chilled run config/s3_to_cyborgdb_http.yaml
        ;;
    3)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}Pipeline stopped.${NC}"