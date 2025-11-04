"""
Configuration module for Revela Streamlit app.
Handles environment variables and Cloud Run OIDC token generation.
"""
import os
from typing import Optional
from dotenv import load_dotenv
import google.auth
from google.auth.transport.requests import Request
import google.oauth2.id_token

# Load environment variables
load_dotenv()


class Config:
    """Application configuration manager."""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "local")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma3:12b-it-qat")
        self.streamlit_port = int(os.getenv("STREAMLIT_SERVER_PORT", "8501"))
        self.streamlit_address = os.getenv("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")
    
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
            return None
        
        try:
            # Get the OIDC token for Cloud Run to Cloud Run invocation
            auth_req = Request()
            target_audience = self.ollama_host
            id_token = google.oauth2.id_token.fetch_id_token(auth_req, target_audience)
            return id_token
        except Exception as e:
            print(f"Error fetching OIDC token: {e}")
            return None
    
    def get_headers(self) -> dict:
        """Get HTTP headers with authentication if needed."""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.is_production:
            token = self.get_auth_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        return headers


# Create global config instance
config = Config()
