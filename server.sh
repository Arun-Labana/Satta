#!/bin/bash
# Simple HTTP server script for macOS/Linux
# Run: bash server.sh

PORT=8000

echo "🚀 Starting server on http://localhost:$PORT"
echo "📂 Serving directory: $(pwd)"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Try Python 3 first, then Python 2, then use PHP as fallback
if command -v python3 &> /dev/null; then
    python3 -m http.server $PORT
elif command -v python &> /dev/null; then
    python -m SimpleHTTPServer $PORT
elif command -v php &> /dev/null; then
    php -S localhost:$PORT
else
    echo "❌ Error: No suitable server found. Please install Python or PHP."
    exit 1
fi

