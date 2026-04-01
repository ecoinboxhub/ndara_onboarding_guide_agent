#!/bin/bash
# ================================================================
# ndara.ai Customer AI - Production Startup Script
# ================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ndara.ai Customer AI - Production Start${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "${YELLOW}Please copy ENV_TEMPLATE.txt to .env and configure it.${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}Warning: OPENAI_API_KEY not set in environment${NC}"
    echo -e "${YELLOW}Make sure it's set in .env file${NC}"
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Get configuration
API_HOST=${API_HOST:-0.0.0.0}
API_PORT=${API_PORT:-8000}
WORKERS=${WORKERS:-4}
LOG_LEVEL=${LOG_LEVEL:-info}

echo -e "${GREEN}Configuration:${NC}"
echo -e "  Host: ${API_HOST}"
echo -e "  Port: ${API_PORT}"
echo -e "  Workers: ${WORKERS}"
echo -e "  Log Level: ${LOG_LEVEL}"
echo ""

# Start the server
echo -e "${GREEN}Starting Customer AI server...${NC}"
echo -e "${GREEN}API will be available at: http://${API_HOST}:${API_PORT}${NC}"
echo -e "${GREEN}API Documentation: http://${API_HOST}:${API_PORT}/docs${NC}"
echo ""

exec gunicorn main:app \
    --config gunicorn_config.py \
    --bind ${API_HOST}:${API_PORT} \
    --workers ${WORKERS} \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level ${LOG_LEVEL}

