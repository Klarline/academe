#!/bin/bash

# Start ALL Academe services (Backend API + Frontend)
# Usage: ./start_all.sh

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Academe - Full Stack${NC}"
echo ""
echo -e "${BLUE}Starting services:${NC}"
echo "  1. Backend API (Port 8000)"
echo "  2. Frontend (Port 3000)"
echo ""
echo -e "${YELLOW}Note: Celery worker must be started separately if needed${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down all services...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend API
echo -e "${GREEN}Starting Backend API...${NC}"
cd "$PROJECT_ROOT"
./scripts/start_api.sh &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 3

# Start Frontend
echo -e "${GREEN}Starting Frontend...${NC}"
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}✅ All services started!${NC}"
echo ""
echo "📡 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🎨 Frontend: http://localhost:3000"
echo ""
echo -e "${YELLOW}Press CTRL+C to stop all services${NC}"
echo ""

# Wait for processes
wait
