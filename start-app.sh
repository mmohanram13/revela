#!/bin/bash
# Quick start script for Revela Streamlit app

echo "🚀 Starting Revela Streamlit App..."

# Check if .env exists
if [ ! -f "application/.env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp application/.env.example application/.env
    echo "✓ Created application/.env - please configure if needed"
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
uv add streamlit python-dotenv pillow google-auth requests ollama watchdog

# Run the app
echo ""
echo "✓ Starting Streamlit app..."
echo "🌐 Access the app at: http://localhost:8501"
echo ""
uv run streamlit run application/app.py
