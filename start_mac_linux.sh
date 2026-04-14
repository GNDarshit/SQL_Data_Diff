#!/bin/bash
echo "============================================"
echo "  SQL Diff - Starting Server"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Install from https://python.org"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install flask flask-cors pyodbc --quiet

echo ""
echo "Starting server on http://localhost:5000"
echo "Press Ctrl+C to stop."
echo ""

# Open browser
sleep 2 && open http://localhost:5000 2>/dev/null || xdg-open http://localhost:5000 2>/dev/null &

# Start server
python3 server.py
