@echo off
REM Quick start script for Revela Flask app (Windows)

echo 🚀 Starting Revela Flask App...

REM Check if .env exists
if not exist ".env" (
    echo ⚠️  .env file not found. Creating from .env.example...
    if exist ".env.example" (
        copy .env.example .env
        echo ✓ Created .env - please configure if needed
    )
)

REM Activate virtual environment if it exists
if exist ".venv" (
    echo ✓ Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo ⚠️  Virtual environment not found. Creating one...
    uv venv
    call .venv\Scripts\activate.bat
)

REM Install/update dependencies
echo 📦 Installing dependencies...
uv sync

REM Ensure gunicorn is installed
echo 📦 Ensuring gunicorn is installed...
uv pip install gunicorn

REM Run the app with gunicorn
echo.
echo ✓ Starting Flask app with gunicorn...
echo 🌐 Access the app at: http://localhost:8080
echo.
uv run gunicorn --bind 0.0.0.0:8080 --workers 1 --timeout 120 --reload src.app:app
