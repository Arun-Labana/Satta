#!/bin/bash
# Start script for BSE Announcements Dashboard with Kite API

cd "$(dirname "$0")"

echo "🚀 Starting BSE Announcements Dashboard..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if kiteconnect is installed
if ! python -c "import kiteconnect" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "⚠️  ngrok not found. Installing..."
    brew install ngrok
fi

echo ""
echo "✅ All dependencies installed!"
echo ""
echo "📋 Next steps:"
echo "1. Start ngrok in a separate terminal: ngrok http 8000"
echo "2. Copy the HTTPS URL from ngrok"
echo "3. Use that URL in Kite app settings and dashboard config"
echo ""
echo "Starting server..."
echo ""

# Start the server
python3 proxy_server.py

