#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

PORT="${PORT:-5050}"

# Detect Local IP address
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo "================================================================="
echo "   Question Paper Studio - Production Server"
echo "   Multi-Page Exam Generator • Auto-Fitting • PDF & DOCX"
echo "================================================================="
echo " Local Access:    http://localhost:$PORT"
echo " Network Access:  http://$LOCAL_IP:$PORT  (Use this on your phone/tablet)"
echo "================================================================="

# Create necessary directories
mkdir -p uploads exports question_banks/extracted_imgs

# Check if Gunicorn is available, otherwise use Python3
if command -v gunicorn >/dev/null 2>&1; then
    echo "Starting with Gunicorn production WSGI server (3 workers)..."
    exec gunicorn --bind "0.0.0.0:$PORT" --workers 3 --timeout 120 app:app
else
    echo "Starting with Python Flask server..."
    exec python3 app.py
fi
