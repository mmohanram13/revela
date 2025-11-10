#!/bin/bash
# Quick start script for Revela Flask app

echo "🚀 Starting Revela Flask App..."

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env - please configure if needed"
    fi
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "✓ Activating virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  Virtual environment not found. Creating one..."
    uv venv
    source .venv/bin/activate
fi

# Install/update dependencies
echo "📦 Installing dependencies..."
uv sync

# Ensure gunicorn is installed
echo "📦 Ensuring gunicorn is installed..."
uv pip install gunicorn

# Run the app with gunicorn
echo ""
echo "✓ Starting Flask app with gunicorn..."
echo "🌐 Access the app at: http://localhost:8080"
echo ""
uv run gunicorn --bind 0.0.0.0:8080 --workers 1 --timeout 120 --reload src.app:app
