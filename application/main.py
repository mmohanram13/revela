"""
Main entry point for Revela Flask application.
"""
from app import app
from config import config


def main():
    """Start the Flask application."""
    print("=" * 50)
    print("Starting Revela Flask Application")
    print("=" * 50)
    print(f"Environment: {config.environment}")
    print(f"Host: {config.server_address}")
    print(f"Port: {config.server_port}")
    print(f"Ollama URL: {config.ollama_host}")
    print(f"Model: {config.ollama_model}")
    print("=" * 50)
    
    app.run(
        host=config.server_address,
        port=config.server_port,
        debug=(config.environment == 'local')
    )


if __name__ == "__main__":
    main()
