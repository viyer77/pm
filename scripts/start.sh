#!/bin/bash
# Start script for macOS/Linux

set -e

echo "Building Docker image..."
docker compose build

echo "Starting container..."
docker compose up -d

echo "Waiting for service to be ready..."
sleep 2

echo ""
echo "✓ Service started successfully!"
echo "Frontend: http://localhost:8000"
echo "API Test: curl http://localhost:8000/api/test"
echo "Health: curl http://localhost:8000/health"
echo ""
echo "To stop: ./scripts/stop.sh"
