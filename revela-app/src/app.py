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
import re
import polars as pl

from src.config_module import config
from src.ollama_client import ollama_client
from src.session_manager import session_manager
from src.llm_code_executor import CodeExecutor, create_chart_prompt

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
                # For tables, load data into Polars and get comprehensive stats
                numeric_stats = summary.get('numeric_stats', {})
                stats_text = ""
                if numeric_stats:
                    stats_text = "\n**Numeric Statistics:**\n"
                    for col, stats in numeric_stats.items():
                        stats_text += f"- {col}: mean={stats.get('mean', 'N/A')}, min={stats.get('min', 'N/A')}, max={stats.get('max', 'N/A')}\n"
                
                prompt = f"""Analyze this table data and provide 3-5 quick, actionable insights.

**Table Information:**
- Rows: {summary.get('row_count', 0)}
- Columns: {summary.get('column_count', 0)}
- Column Names: {', '.join(summary.get('columns', []))}
- Data Types: {json.dumps(summary.get('dtypes', {}), indent=2)}

{stats_text}

**Sample Data (first 5 rows):**
{json.dumps(summary.get('sample_rows', []), indent=2)}

Provide brief, clear insights about patterns, trends, or notable data points.

Format your response in markdown with:
- Use ## for section headings
- Use **bold** for emphasis on key points
- Use numbered lists for insights
- Keep each insight concise (1-2 sentences)"""
                
            elif data_type in ['image', 'canvas']:
                # For images, validate if it's a chart and analyze with vision
                logger.info(f"Processing image/canvas data. Has image_data: {temp_session.image_data is not None}")
                
                validation = summary.get('validation', {})
                
                if not validation.get('has_chart', True):
                    logger.warning(f"Preliminary validation failed: {validation}")
                    return jsonify({
                        'success': False,
                        'error': 'No chart or visualization detected in image',
                        'details': validation.get('reason', 'Image validation failed')
                    }), 400
                
                # Use LLM vision to validate chart
                if temp_session.image_data:
                    logger.info("Validating image with LLM vision...")
                    alt_text = summary.get('alt', '')
                    chart_validation = ollama_client.validate_image_for_chart(
                        temp_session.image_data, 
                        alt_text=alt_text
                    )
                    logger.info(f"Chart validation result: {chart_validation}")
                    
                    if not chart_validation.get('is_chart', False):
                        logger.warning(f"LLM says not a chart: {chart_validation}")
                        return jsonify({
                            'success': False,
                            'error': 'No chart or visualization detected in image',
                            'details': chart_validation.get('description', 'Not a chart')
                        }), 400
                    
                    # Analyze chart with vision
                    prompt = f"""Analyze this chart/visualization and provide 3-5 quick, actionable insights.

**Image Information:**
- Dimensions: {summary.get('width')}x{summary.get('height')}
- Alt Text: {alt_text if alt_text else 'N/A'}
- Detected Chart Type: {chart_validation.get('chart_type', 'unknown')}

Based on what you see in the image and the context provided, provide specific insights about:
- What data is being shown
- Key trends or patterns
- Notable data points or outliers
- What the visualization tells us

Format your response in markdown with:
- Use ## for section headings
- Use **bold** for emphasis on key points
- Use numbered lists for insights
- Be specific about what you observe in the chart"""
                    
                    image_to_send = temp_session.image_data
                else:
                    # Fallback without image
                    prompt = f"""Based on the metadata, provide general insights about this visualization.

Image Information:
- Dimensions: {summary.get('width')}x{summary.get('height')}
- Alt Text: {summary.get('alt', 'N/A')}

Provide insights based on typical chart patterns."""
                    image_to_send = None
                
                # Get insights from LLM with image
                insights_text = ""
                for chunk in ollama_client.generate(prompt, image=image_to_send):
                    insights_text += chunk
                    
                return jsonify({
                    'success': True,
                    'insights': insights_text,
                    'summary': summary,
                    'chart_validation': chart_validation if temp_session.image_data else None
                })
            
            else:
                return jsonify({'error': 'Unsupported data type'}), 400
                
            # Get insights from LLM (for table data)
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
        logger.error(f"Error generating quick insights: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/deep-analyse', methods=['POST', 'OPTIONS'])
def deep_analyse():
    """Handle conversational analysis for ongoing sessions with data query and chart generation"""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        
        session_id = data.get('sessionId')
        message = data.get('message', '')
        
        logger.info(f"Deep analyse request - sessionId: {session_id}, message length: {len(message)}")
        
        if not session_id or not message:
            logger.error(f"Missing required fields - sessionId: {session_id}, message: {bool(message)}")
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Get session
        session = session_manager.get_session(session_id)
        logger.info(f"Session retrieval result - session_id: {session_id}, found: {session is not None}")
        
        if not session:
            logger.error(f"Session not found - session_id: {session_id}, active sessions: {list(session_manager.sessions.keys())}")
            return jsonify({'error': 'Session not found or expired'}), 404
            
        # Add user message to conversation
        session.add_conversation('user', message)
        
        # Build context for LLM
        summary = session.get_summary_stats()
        
        # Check if this is a table or image analysis
        is_table = session.data_type == 'table' and session.df is not None
        is_image = session.data_type in ['image', 'canvas'] and session.image_data is not None
        
        # Build conversation context
        context = f"""You are analyzing data from a web page.

Data Type: {session.data_type}

Data Summary:
{json.dumps(summary, indent=2)}

Conversation History:
"""
        for msg in session.conversation_history[-5:]:  # Last 5 messages for context
            role = msg['role'].capitalize()
            content = msg['content']
            context += f"{role}: {content}\n"
        
        # For table data, use intelligent query system
        if is_table:
            # Step 1: Ask LLM to analyze the question and generate code
            executor = CodeExecutor(session)
            
            # Build conversation context for code generation
            conversation_context = ""
            if len(session.conversation_history) > 1:
                conversation_context = "\n**Previous Conversation:**\n"
                for msg in session.conversation_history[-4:]:  # Last 4 messages (2 exchanges)
                    role = msg['role'].capitalize()
                    content = msg['content'][:200]  # Truncate long messages
                    conversation_context += f"{role}: {content}\n"
                conversation_context += "\n"
            
            # Create a focused prompt that requests executable code
            code_prompt = f"""You are a data analysis assistant with access to a Polars DataFrame called 'df'.

**Dataset Information:**
- Rows: {summary.get('row_count', 0)}
- Columns: {summary.get('columns', [])}
- Sample Data (first 3 rows): {json.dumps(summary.get('sample_rows', [])[:3], indent=2)}

{conversation_context}**Current User Question:** {message}

**IMPORTANT Instructions:**
1. Write Polars code to answer the question
2. Store the final result in a variable called 'result'
3. Return ONLY the Python code, no explanations
4. DO NOT include import statements - 'pl' and 'df' are already available
5. Use pl.col() for column references
6. Handle string/numeric conversions as needed
7. For multi-row results, use .to_dict() or select first row with [0] if needed
8. NEVER use .item() unless you're certain the result is a single value (1x1)

**Example for single value (1x1 result):**
```python
result = df.filter(pl.col('country') == 'India').select('gdp').item()
```

**Example for multi-row result:**
```python
result = df.filter(pl.col('region') == 'Asia').select(['country', 'gdp']).head(5).to_dict()
```

**Example for aggregation:**
```python
result = df.select(pl.col('gdp').sum()).item()
```

Now write ONLY the code (no imports, no explanations) to answer: {message}"""

            # Get code from LLM
            code_response = ""
            for chunk in ollama_client.generate(code_prompt, stream=False):
                code_response += chunk
            
            logger.info(f"LLM code response: {code_response}")
            
            # Parse and execute the code
            parsed = executor.parse_llm_response_for_code(code_response)
            
            result_data = None
            execution_result = None
            
            if parsed['has_code'] and parsed['polars_code']:
                try:
                    execution_result = executor.execute_polars_code(parsed['polars_code'])
                    result_data = execution_result
                    logger.info(f"Code executed successfully: {execution_result}")
                except Exception as e:
                    logger.error(f"Error executing code: {e}")
                    result_data = {'error': str(e)}
            
            # Step 2: Generate natural language response with the actual result
            explanation_prompt = f"""Based on this data query result, provide a clear, concise answer to the user's question.

**User Question:** {message}

**Dataset Context:** Table with {summary.get('row_count')} rows, columns: {', '.join(summary.get('columns', []))}

"""
            
            if execution_result and execution_result.get('success'):
                explanation_prompt += f"**Query executed successfully. Result:**\n{json.dumps(execution_result.get('data'), indent=2)}\n\n"
                explanation_prompt += "Provide a natural language answer that includes the actual data values. Be specific and cite the numbers in your response."
            else:
                error_msg = result_data.get('error') if result_data else 'No code was generated to answer this question'
                explanation_prompt += f"**Error occurred:** {error_msg}\n\n"
                explanation_prompt += "Explain the error to the user in simple terms and suggest what might be wrong or how to rephrase the question."

            # Get natural language explanation
            response_text = ""
            for chunk in ollama_client.generate(explanation_prompt):
                response_text += chunk
            
            # Add error info if code execution failed (for display in UI)
            if execution_result and not execution_result.get('success'):
                # Format error nicely for display
                error_display = f"\n\n⚠️ **Query Error:**\n\n```\n{result_data.get('error', 'Unknown error')}\n```"
                response_text += error_display
            
            # Check if chart would be helpful
            chart_image = None
            if 'chart' in message.lower() or 'plot' in message.lower() or 'visualize' in message.lower():
                # Ask LLM for chart suggestion
                data_summary = json.dumps(execution_result.get('data') if execution_result else {}, indent=2)
                chart_prompt = f"""Suggest a chart specification for this data.

Question: {message}
Data: {data_summary}

Respond with ONLY a JSON object:
```json
{{
  "type": "bar|line|scatter|pie",
  "x_col": "column_name",
  "y_col": "column_name", 
  "title": "Chart Title"
}}
```"""
                
                chart_response = ""
                for chunk in ollama_client.generate(chart_prompt, stream=False):
                    chart_response += chunk
                
                chart_parsed = executor.parse_llm_response_for_code(chart_response)
                if chart_parsed['has_chart']:
                    try:
                        chart_image = session.generate_chart(chart_parsed['chart_spec'])
                        logger.info(f"Generated chart successfully")
                    except Exception as e:
                        logger.error(f"Error generating chart: {e}")
            
            # Add to conversation
            session.add_conversation('assistant', response_text)
            
            return jsonify({
                'success': True,
                'response': response_text,
                'has_chart': bool(chart_image),
                'chart': chart_image
            })
            
        elif is_image:
            # For images, use vision analysis
            full_prompt = f"""{context}

User Question: {message}

Analyze the image and answer the user's question based on what you can see in the visualization.

Format your response in markdown with:
- Use ## for section headings
- Use **bold** for emphasis on key findings
- Be specific about what you observe in the chart"""
            
            # Get response from LLM with image
            response_text = ""
            for chunk in ollama_client.generate(full_prompt, image=session.image_data):
                response_text += chunk
            
            # Check if user wants a chart generated
            chart_image = None
            if any(keyword in message.lower() for keyword in ['chart', 'plot', 'graph', 'visualize', 'show me']):
                logger.info("User requested chart generation from image analysis")
                
                # Ask LLM to extract data and suggest chart
                chart_request_prompt = f"""Based on the image you just analyzed and the user's question: "{message}"

Extract the key data points you can see in the image and suggest how to visualize them.

Respond ONLY with a JSON object in this format:
```json
{{
  "data": {{"Country": ["India", "Canada"], "GDP": [4.12, 2.28]}},
  "chart_type": "bar",
  "x_col": "Country",
  "y_col": "GDP",
  "title": "GDP Comparison",
  "x_label": "Country",
  "y_label": "GDP (USD Trillion)"
}}
```

Extract actual values from the image. Be precise with numbers."""
                
                chart_spec_text = ""
                for chunk in ollama_client.generate(chart_request_prompt, image=session.image_data, stream=False):
                    chart_spec_text += chunk
                
                logger.info(f"Chart specification from LLM: {chart_spec_text}")
                
                # Parse the chart specification
                try:
                    # Extract JSON from response
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', chart_spec_text, re.DOTALL)
                    if json_match:
                        chart_spec = json.loads(json_match.group())
                        
                        # Generate chart using the extracted data
                        if 'data' in chart_spec and chart_spec['data']:
                            logger.info(f"Generating chart from extracted data: {chart_spec['data']}")
                            
                            # Create a temporary DataFrame from the extracted data
                            temp_df = pl.DataFrame(chart_spec['data'])
                            
                            # Create chart specification for session.generate_chart
                            chart_params = {
                                'type': chart_spec.get('chart_type', 'bar'),
                                'x_col': chart_spec.get('x_col'),
                                'y_col': chart_spec.get('y_col'),
                                'title': chart_spec.get('title', 'Chart'),
                                'x_label': chart_spec.get('x_label'),
                                'y_label': chart_spec.get('y_label')
                            }
                            
                            # Temporarily set the DataFrame in session
                            original_df = session.df
                            session.df = temp_df
                            
                            try:
                                chart_image = session.generate_chart(chart_params)
                                logger.info("Successfully generated chart from image data")
                            finally:
                                # Restore original DataFrame
                                session.df = original_df
                                
                except Exception as e:
                    logger.error(f"Error generating chart from image: {e}", exc_info=True)
            
            # Add assistant response to conversation
            session.add_conversation('assistant', response_text)
            
            return jsonify({
                'success': True,
                'response': response_text,
                'has_chart': bool(chart_image),
                'chart': chart_image
            })
        
        else:
            # Fallback for other data types
            full_prompt = f"""{context}

User Question: {message}

Provide a clear, concise answer based on the available data.

Format your response in markdown with:
- Use ## for section headings
- Use **bold** for emphasis on key findings
- Use bullet points or numbered lists for clarity"""
            
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
        logger.error(f"Error in deep analyse: {e}", exc_info=True)
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
