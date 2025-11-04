"""
Ollama client module for Revela Streamlit app.
Handles communication with Ollama API with environment-based authentication.
"""
import base64
from typing import Optional, Dict, Any, Generator
import requests
from io import BytesIO
from PIL import Image

from config import config


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self):
        self.base_url = config.get_ollama_url()
        self.model = config.ollama_model
        self.headers = config.get_headers()
    
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
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                stream=stream,
                timeout=120
            )
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
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


# Create global client instance
ollama_client = OllamaClient()
