#!/bin/bash

# Start Academe API Server
# Usage: ./start_api.sh

cd "$(dirname "$0")"

echo "🚀 Starting Academe API v0.5..."
echo ""

# Set PYTHONPATH to include src directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Start API with uvicorn
echo "📡 API will be available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
echo ""
echo "Press CTRL+C to stop"
echo ""

python3 -m uvicorn api.main:app \
  --reload \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level info
