#!/bin/bash
# Start Celery worker for Academe

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Academe Celery Worker...${NC}"
echo ""

# Check if Redis is running
if ! nc -z localhost 6379 2>/dev/null; then
    echo -e "${YELLOW}Warning: Redis not detected on localhost:6379${NC}"
    echo "Please start Redis first:"
    echo "  docker run -d -p 6379:6379 redis"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Redis is running${NC}"
echo ""

# Start Celery worker
echo "Starting worker with:"
echo "  - Queues: memory (high priority), documents (medium priority), default"
echo "  - Concurrency: 4 workers"
echo "  - Log level: info"
echo ""

# Change to project root, then backend directory
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
cd backend

celery -A core.celery_config worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=memory,documents,default \
    --max-tasks-per-child=1000 \
    --time-limit=300 \
    --soft-time-limit=240
