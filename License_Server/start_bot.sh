#!/bin/bash
# BigMotion Telegram License Bot - Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found!"
    exit 1
fi

source venv/bin/activate

echo "🤖 Starting BigMotion Telegram License Bot..."
python3 telegram_license_bot.py
