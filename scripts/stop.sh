#!/bin/bash
# Stop script for macOS/Linux

set -e

echo "Stopping container..."
docker compose down

echo "✓ Container stopped successfully!"
