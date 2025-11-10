"""
Revela Flask App
"""
from flask import Flask, render_template, request, jsonify, Response
from PIL import Image
import io
import logging
import base64
from pathlib import Path
import json

from src.config_module import config
from src.ollama_client import ollama_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("=== Revela Flask App Starting ===")
logger.info(f"Environment: {config.environment}")
logger.info(f"Ollama URL: {config.ollama_host}")

# Get the absolute path to the images directory
CURRENT_DIR = Path(__file__).parent.parent
LOGO_PATH = CURRENT_DIR / "ui" / "static" / "images" / "logo.png"

# Initialize Flask app
app = Flask(__name__, 
            template_folder='../ui/templates',
            static_folder='../ui/static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


def get_base64_image_from_path(image_path: Path) -> str:
    """Convert image file to base64 string."""
    try:
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception as e:
        logger.warning(f"Could not load image from {image_path}: {e}")
        return ""


def process_image_data(image_data: str) -> Image.Image:
    """Process base64 image data and return PIL Image."""
    try:
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        return image
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return None


@app.route('/')
def index():
    """Render the main page."""
    # Check Ollama connection
    logger.info("Performing Ollama health check...")
    health_check_result = ollama_client.check_health()
    logger.info(f"Health check result: {health_check_result}")
    
    # Get logo as base64
    logo_base64 = get_base64_image_from_path(LOGO_PATH) if LOGO_PATH.exists() else ""
    
    return render_template(
        'index.html',
        logo_base64=logo_base64,
        ollama_healthy=health_check_result,
        environment=config.environment,
        model=config.ollama_model,
        ollama_host=config.ollama_host
    )


@app.route('/health')
def health():
    """Health check endpoint."""
    ollama_healthy = ollama_client.check_health()
    return jsonify({
        'status': 'healthy' if ollama_healthy else 'degraded',
        'ollama': ollama_healthy,
        'environment': config.environment
    })


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze endpoint that streams the response."""
    data = request.get_json()
    prompt = data.get('prompt', '')
    image_data = data.get('image', '')
    
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    # Process image if provided
    image = None
    if image_data:
        image = process_image_data(image_data)
        if image is None:
            return jsonify({'error': 'Invalid image data'}), 400
    
    def generate():
        """Generator function for streaming response."""
        try:
            for chunk in ollama_client.generate(prompt, image=image):
                # Send each chunk as a JSON object
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Error during analysis: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


def create_app():
    """Application factory function."""
    return app
