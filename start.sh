#!/bin/bash
# Start the enhanced RAG application with environment variables

API_HOST=${API_HOST:-0.0.0.0}
API_PORT=${API_PORT:-3000}

echo "Starting RAG Application on $API_HOST:$API_PORT"
uvicorn src.main_enhanced:app --host $API_HOST --port $API_PORT --reload
