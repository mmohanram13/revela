"""
Configuration module for Revela Flask app.
Handles environment variables and Cloud Run OIDC token generation.
"""
import os
import logging
from typing import Optional
from dotenv import load_dotenv
import google.auth
from google.auth.transport.requests import Request
import google.oauth2.id_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class Config:
    """Application configuration manager."""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "local")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma3:12b-it-qat")
        self.server_port = int(os.getenv("SERVER_PORT", "8501"))
        self.server_address = os.getenv("SERVER_ADDRESS", "0.0.0.0")
        
        # Log configuration on initialization
        logger.info(f"=== Configuration Initialized ===")
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Ollama Host: {self.ollama_host}")
        logger.info(f"Ollama Model: {self.ollama_model}")
        logger.info(f"Is Production: {self.is_production}")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_local(self) -> bool:
        """Check if running in local environment."""
        return self.environment.lower() == "local"
    
    def get_ollama_url(self) -> str:
        """Get the appropriate Ollama URL based on environment."""
        return self.ollama_host
    
    def get_auth_token(self) -> Optional[str]:
        """
        Get authentication token for Cloud Run service invocation.
        Returns None for local environment.
        """
        if self.is_local:
            logger.info("Running in local mode, skipping authentication")
            return None
        
        try:
            logger.info(f"Fetching OIDC token for target audience: {self.ollama_host}")
            # Get the OIDC token for Cloud Run to Cloud Run invocation
            auth_req = Request()
            target_audience = self.ollama_host
            id_token = google.oauth2.id_token.fetch_id_token(auth_req, target_audience)
            logger.info("Successfully fetched OIDC token")
            return id_token
        except Exception as e:
            logger.error(f"Error fetching OIDC token: {e}", exc_info=True)
            return None
    
    def get_headers(self) -> dict:
        """Get HTTP headers with authentication if needed."""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.is_production:
            logger.info("Production mode: Adding authentication header")
            token = self.get_auth_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                logger.info("Authorization header added successfully")
            else:
                logger.warning("Failed to get auth token, proceeding without authentication")
        else:
            logger.info("Non-production mode: Skipping authentication")
        
        return headers


# Create global config instance
config = Config()
