"""
Revela Flask App - Backend API for ephemeral data analysis
"""
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from PIL import Image
import io
import logging
import base64
from pathlib import Path
import json

from src.config_module import config
from src.ollama_client import ollama_client
from src.session_manager import session_manager

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

# Enable CORS for extension - Allow all origins since content script runs on any website
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # Allow all origins (content script can be on any website)
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": False
    }
})

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
        'environment': config.environment,
        'active_sessions': len(session_manager.sessions)
    })


# API Endpoints for Chrome Extension

@app.route('/api/session/start', methods=['POST', 'OPTIONS'])
def start_session():
    """Start a new analysis session"""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        
        session_id = data.get('sessionId')
        element_data = data.get('data', {})
        url = data.get('url', '')
        
        if not session_id or not element_data:
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Create session (using provided ID from extension)
        # We'll store with the extension-provided ID
        from src.session_manager import AnalysisSession
        session = AnalysisSession(session_id, element_data, url)
        
        with session_manager.lock:
            session_manager.sessions[session_id] = session
            
        logger.info(f"Started session {session_id} for {element_data.get('type')}")
        
        # Get summary stats
        summary = session.get_summary_stats()
        
        return jsonify({
            'success': True,
            'sessionId': session_id,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/quick-insights', methods=['POST', 'OPTIONS'])
def quick_insights():
    """Generate quick insights without creating persistent session"""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        
        session_id = data.get('sessionId')
        element_data = data.get('data', {})
        url = data.get('url', '')
        
        if not element_data:
            return jsonify({'error': 'Missing data'}), 400
            
        data_type = element_data.get('type')
        
        # Create temporary session for analysis
        from src.session_manager import AnalysisSession
        temp_session = AnalysisSession(session_id, element_data, url)
        
        try:
            summary = temp_session.get_summary_stats()
            
            # Build prompt for LLM
            if data_type == 'table':
                prompt = f"""Analyze this table data and provide 3-5 quick, actionable insights.

Table Information:
- Rows: {summary.get('row_count', 0)}
- Columns: {summary.get('column_count', 0)}
- Column Names: {', '.join(summary.get('columns', []))}

Sample Data:
{format_sample_rows(summary.get('sample_rows', []), summary.get('columns', []))}

Provide brief, clear insights about patterns, trends, or notable data points.

Format your response in markdown with:
- Use ## for section headings
- Use **bold** for emphasis on key points
- Use numbered lists for insights
- Keep each insight concise (1-2 sentences)"""
                
            elif data_type in ['image', 'canvas']:
                prompt = f"""Analyze this chart/visualization and provide 3-5 quick insights.

Image Information:
- Dimensions: {summary.get('width')}x{summary.get('height')}
- Alt Text: {summary.get('alt', 'N/A')}

Based on typical chart patterns, what insights might this visualization be showing?

Format your response in markdown with:
- Use ## for section headings
- Use **bold** for emphasis on key points
- Use numbered lists for insights
- Keep each insight concise (1-2 sentences)"""
            
            else:
                return jsonify({'error': 'Unsupported data type'}), 400
                
            # Get insights from LLM
            insights_text = ""
            for chunk in ollama_client.generate(prompt):
                insights_text += chunk
                
            return jsonify({
                'success': True,
                'insights': insights_text,
                'summary': summary
            })
            
        finally:
            # Clean up temporary session
            temp_session.close()
            
    except Exception as e:
        logger.error(f"Error generating quick insights: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/deep-analyse', methods=['POST', 'OPTIONS'])
def deep_analyse():
    """Handle conversational analysis for ongoing sessions"""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        
        session_id = data.get('sessionId')
        message = data.get('message', '')
        
        if not session_id or not message:
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found or expired'}), 404
            
        # Add user message to conversation
        session.add_conversation('user', message)
        
        # Build context for LLM
        summary = session.get_summary_stats()
        
        # Build conversation context
        context = f"""You are analyzing data from a web page.

Data Summary:
{json.dumps(summary, indent=2)}

Conversation History:
"""
        for msg in session.conversation_history[-5:]:  # Last 5 messages for context
            role = msg['role'].capitalize()
            content = msg['content']
            context += f"{role}: {content}\n"
            
        # Current question
        full_prompt = f"""{context}

User Question: {message}

Provide a clear, concise answer based on the data. If the question requires data analysis, explain your findings.

Format your response in markdown with:
- Use ## for section headings
- Use **bold** for emphasis on key findings
- Use bullet points or numbered lists for clarity
- Use code blocks with ``` for data examples if needed"""
        
        # Get response from LLM
        response_text = ""
        for chunk in ollama_client.generate(full_prompt):
            response_text += chunk
            
        # Add assistant response to conversation
        session.add_conversation('assistant', response_text)
        
        return jsonify({
            'success': True,
            'response': response_text
        })
        
    except Exception as e:
        logger.error(f"Error in deep analyse: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/end', methods=['POST', 'OPTIONS'])
def end_session():
    """End an analysis session"""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        session_id = data.get('sessionId')
        
        if not session_id:
            return jsonify({'error': 'Missing sessionId'}), 400
            
        session_manager.end_session(session_id)
        
        return jsonify({
            'success': True,
            'message': 'Session ended'
        })
        
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        return jsonify({'error': str(e)}), 500


def format_sample_rows(rows: list, columns: list) -> str:
    """Format sample rows for display in prompt"""
    if not rows or not columns:
        return "No data available"
        
    # Create a simple text table
    result = []
    result.append(' | '.join(columns))
    result.append('-' * (len(' | '.join(columns))))
    
    for row in rows[:5]:  # Max 5 rows
        result.append(' | '.join(str(cell) for cell in row))
        
    return '\n'.join(result)


# Original endpoints for web interface

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
