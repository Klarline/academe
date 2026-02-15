#!/bin/bash

# Start Academe Frontend
# Usage: ./start_frontend.sh

cd "$(dirname "$0")/../frontend"

echo "🎨 Starting Academe Frontend..."
echo ""
echo "📱 Frontend will be available at: http://localhost:3000"
echo ""
echo "Press CTRL+C to stop"
echo ""

npm run dev
