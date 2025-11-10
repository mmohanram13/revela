"""
Ollama client module for Revela app.
Handles communication with Ollama API with environment-based authentication.
"""
import base64
import logging
from typing import Optional, Dict, Any, Generator
import requests
from io import BytesIO
from PIL import Image

from src.config_module import config

# Configure logging
logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self):
        self.base_url = config.get_ollama_url()
        self.model = config.ollama_model
        self.headers = config.get_headers()
        
        logger.info(f"=== OllamaClient Initialized ===")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Model: {self.model}")
        logger.info(f"Headers keys: {list(self.headers.keys())}")
    
    def generate(
        self,
        prompt: str,
        image: Optional[Image.Image] = None,
        stream: bool = True
    ) -> Generator[str, None, None]:
        """
        Generate response from Ollama model.
        
        Args:
            prompt: User prompt text
            image: Optional PIL Image object
            stream: Whether to stream the response
            
        Yields:
            Generated text chunks
        """
        url = f"{self.base_url}/api/generate"
        
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }
        
        # Add image if provided
        if image:
            payload["images"] = [self._encode_image(image)]
            logger.info(f"Image added to payload")
        
        logger.info(f"Sending generate request to {url}")
        logger.debug(f"Payload: model={self.model}, stream={stream}, has_image={image is not None}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                stream=stream,
                timeout=120
            )
            logger.info(f"Response status code: {response.status_code}")
            response.raise_for_status()
            
            if stream:
                for line in response.iter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
            else:
                data = response.json()
                if "response" in data:
                    yield data["response"]
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Ollama: {str(e)}", exc_info=True)
            yield f"Error communicating with Ollama: {str(e)}"
    
    def _encode_image(self, image: Image.Image) -> str:
        """
        Encode PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            
        Returns:
            Base64 encoded image string
        """
        buffered = BytesIO()
        # Convert RGBA to RGB if necessary
        if image.mode == "RGBA":
            image = image.convert("RGB")
        image.save(buffered, format="JPEG")
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode("utf-8")
    
    def check_health(self) -> bool:
        """
        Check if Ollama service is available.
        
        Returns:
            True if service is healthy, False otherwise
        """
        url = f"{self.base_url}/api/tags"
        logger.info(f"=== Health Check ===")
        logger.info(f"Checking Ollama health at: {url}")
        logger.info(f"Headers: {list(self.headers.keys())}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            logger.info(f"Health check response status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("✓ Ollama service is healthy")
                return True
            else:
                logger.warning(f"✗ Ollama service returned status {response.status_code}")
                logger.warning(f"Response body: {response.text[:500]}")
                return False
                
        except requests.exceptions.Timeout as e:
            logger.error(f"✗ Timeout connecting to Ollama service: {e}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"✗ Connection error to Ollama service: {e}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Request exception during health check: {e}", exc_info=True)
            return False


# Create global client instance
ollama_client = OllamaClient()
