#!/bin/bash
# BigMotion License Server - Startup Script
# Run on your Linux VPS/server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check .env exists
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found!"
    echo "   Copy .env.example to .env and fill in your values."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q

echo "🔐 Starting BigMotion License Server..."
# Use gunicorn for production (4 workers)
gunicorn --workers 4 --bind 0.0.0.0:5000 --timeout 120 \
         --access-logfile access.log --error-logfile error.log \
         "license_server:app"
