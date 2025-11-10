"""
Session Manager for Revela
Manages ephemeral analysis sessions with Polars DataFrames for advanced analytics
"""

import polars as pl
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import logging
import threading
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import uuid
from html.parser import HTMLParser
import io
import base64
import json
from PIL import Image

logger = logging.getLogger(__name__)


class HTMLTableParser(HTMLParser):
    """Parse HTML table into structured data"""
    
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = []
        self.current_row = []
        self.current_cell = []
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
            self.current_table = []
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ['td', 'th'] and self.in_row:
            self.in_cell = True
            self.current_cell = []
            
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
            if self.current_table:
                self.tables.append(self.current_table)
            self.current_table = []
        elif tag == 'tr' and self.in_row:
            self.in_row = False
            if self.current_row:
                self.current_table.append(self.current_row)
            self.current_row = []
        elif tag in ['td', 'th'] and self.in_cell:
            self.in_cell = False
            cell_text = ''.join(self.current_cell).strip()
            self.current_row.append(cell_text)
            self.current_cell = []
            
    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)
            
    def get_tables(self):
        return self.tables


class AnalysisSession:
    """Represents a single ephemeral analysis session with Polars DataFrame"""
    
    def __init__(self, session_id: str, data: Dict[str, Any], url: str):
        self.session_id = session_id
        self.data = data
        self.url = url
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.df: Optional[pl.DataFrame] = None
        self.data_type = data.get('type', 'unknown')
        self.conversation_history = []
        self.image_data: Optional[Image.Image] = None
        
        # Initialize data based on type
        if self.data_type == 'table':
            self._load_table_data()
        elif self.data_type in ['image', 'canvas']:
            self._load_image_data()
        
    def _load_table_data(self):
        """Parse HTML table and load into Polars DataFrame"""
        try:
            html_content = self.data.get('html', '')
            
            # Parse HTML table
            parser = HTMLTableParser()
            parser.feed(html_content)
            tables = parser.get_tables()
            
            if not tables:
                logger.warning(f"No tables found in HTML for session {self.session_id}")
                return
                
            # Use the first table
            table_data = tables[0]
            
            if len(table_data) < 2:
                logger.warning(f"Table has insufficient rows for session {self.session_id}")
                return
                
            # First row as headers, rest as data
            headers = table_data[0]
            rows = table_data[1:]
            
            # Clean headers (make them valid column names)
            clean_headers = []
            for i, header in enumerate(headers):
                clean_header = str(header).strip().replace(' ', '_').replace('-', '_')
                clean_header = ''.join(c for c in clean_header if c.isalnum() or c == '_')
                if not clean_header or clean_header[0].isdigit():
                    clean_header = f'column_{i}'
                clean_headers.append(clean_header.lower())
            
            # Ensure unique headers
            seen = {}
            unique_headers = []
            for header in clean_headers:
                if header in seen:
                    seen[header] += 1
                    unique_headers.append(f"{header}_{seen[header]}")
                else:
                    seen[header] = 0
                    unique_headers.append(header)
            
            # Create dictionary for DataFrame
            data_dict = {header: [] for header in unique_headers}
            
            for row in rows:
                # Pad or truncate row to match header count
                padded_row = list(row)[:len(unique_headers)]
                while len(padded_row) < len(unique_headers):
                    padded_row.append('')
                    
                for header, value in zip(unique_headers, padded_row):
                    data_dict[header].append(value)
            
            # Create Polars DataFrame
            self.df = pl.DataFrame(data_dict)
            
            logger.info(f"Created Polars DataFrame with {self.df.height} rows and {self.df.width} columns for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error loading table data: {e}", exc_info=True)
            raise
            
    def _load_image_data(self):
        """Load and validate image data"""
        try:
            # Store image metadata
            self.image_metadata = {
                'type': self.data.get('type', 'unknown'),
                'width': self.data.get('width', 0),
                'height': self.data.get('height', 0),
                'alt': self.data.get('alt', ''),
                'src': self.data.get('src', '')
            }
            
            logger.info(f"Loading image data for session {self.session_id}")
            logger.info(f"Image metadata: {self.image_metadata}")
            
            # If base64 image data is provided, decode it
            if 'imageData' in self.data and self.data['imageData']:
                image_data = self.data['imageData']
                logger.info(f"Found imageData field, length: {len(image_data)}")
                
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                
                image_bytes = base64.b64decode(image_data)
                self.image_data = Image.open(io.BytesIO(image_bytes))
                logger.info(f"Successfully loaded image data from base64: {self.image_data.size}")
            elif 'src' in self.data and self.data['src']:
                # If no imageData but src is available, fetch from URL
                logger.info(f"No imageData provided, attempting to fetch from URL: {self.data['src']}")
                try:
                    import requests
                    
                    # Add headers to avoid being blocked by websites
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': self.url if self.url else 'https://www.google.com/'
                    }
                    
                    response = requests.get(self.data['src'], timeout=10, headers=headers)
                    response.raise_for_status()
                    self.image_data = Image.open(io.BytesIO(response.content))
                    logger.info(f"Successfully fetched image from URL: {self.image_data.size}")
                except Exception as e:
                    logger.error(f"Failed to fetch image from URL: {e}", exc_info=True)
                    self.image_data = None
            else:
                logger.warning(f"No imageData or src found in data: {list(self.data.keys())}")
            
        except Exception as e:
            logger.error(f"Error loading image data: {e}", exc_info=True)
            
    def validate_chart_image(self) -> Dict[str, Any]:
        """Validate if image contains chart/visualization using basic checks"""
        if not self.image_data:
            return {'has_chart': False, 'reason': 'No image data available'}
        
        try:
            # Basic validation - check image properties
            width, height = self.image_data.size
            
            # Check if image is too small to be a chart
            if width < 100 or height < 100:
                return {'has_chart': False, 'reason': 'Image too small to contain meaningful chart'}
            
            # Check alt text for chart-related keywords
            alt_text = self.image_metadata.get('alt', '').lower()
            chart_keywords = ['chart', 'graph', 'plot', 'diagram', 'visualization', 'data', 'analytics']
            
            has_chart_keyword = any(keyword in alt_text for keyword in chart_keywords)
            
            # Return preliminary validation (LLM will do deeper analysis)
            return {
                'has_chart': True,  # We'll let LLM make final determination
                'preliminary_check': has_chart_keyword,
                'dimensions': f"{width}x{height}",
                'alt_text': alt_text
            }
            
        except Exception as e:
            logger.error(f"Error validating chart image: {e}")
            return {'has_chart': False, 'reason': f'Validation error: {str(e)}'}
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Generate summary statistics for the data"""
        try:
            if self.data_type == 'table' and self.df is not None:
                # Get basic stats
                summary = {
                    'type': 'table',
                    'row_count': self.df.height,
                    'column_count': self.df.width,
                    'columns': self.df.columns,
                    'sample_rows': self.df.head(5).to_dicts(),
                    'dtypes': {col: str(dtype) for col, dtype in zip(self.df.columns, self.df.dtypes)}
                }
                
                # Add basic statistics for numeric columns
                numeric_stats = {}
                for col in self.df.columns:
                    try:
                        # Try to cast to numeric
                        numeric_col = self.df[col].cast(pl.Float64, strict=False)
                        if numeric_col.null_count() < self.df.height:  # Has some valid numeric values
                            numeric_stats[col] = {
                                'mean': float(numeric_col.mean()) if numeric_col.mean() is not None else None,
                                'min': float(numeric_col.min()) if numeric_col.min() is not None else None,
                                'max': float(numeric_col.max()) if numeric_col.max() is not None else None,
                                'null_count': numeric_col.null_count()
                            }
                    except:
                        pass  # Not a numeric column
                
                summary['numeric_stats'] = numeric_stats
                return summary
                
            elif self.data_type in ['image', 'canvas']:
                validation = self.validate_chart_image()
                return {
                    'type': self.data_type,
                    **self.image_metadata,
                    'validation': validation
                }
        except Exception as e:
            logger.error(f"Error getting summary stats: {e}", exc_info=True)
            return {'error': str(e)}
    
    def execute_polars_query(self, query_description: str) -> Dict[str, Any]:
        """
        Execute Polars operations based on natural language query.
        This will be enhanced with LLM to generate actual Polars code.
        """
        if self.df is None:
            return {'error': 'No DataFrame available'}
        
        try:
            # For now, return basic info - will be enhanced with LLM-generated code
            return {
                'success': True,
                'description': query_description,
                'data': self.df.head(10).to_dicts(),
                'shape': {'rows': self.df.height, 'columns': self.df.width}
            }
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {'error': str(e)}
    
    def generate_chart(self, chart_spec: Dict[str, Any]) -> Optional[str]:
        """
        Generate matplotlib chart based on specification.
        
        Args:
            chart_spec: Dictionary with chart specifications
                - type: 'bar', 'line', 'scatter', 'pie', 'hist'
                - x_col: column for x-axis
                - y_col: column for y-axis
                - title: chart title
                - x_label: optional custom x-axis label
                - y_label: optional custom y-axis label
                
        Returns:
            Base64 encoded PNG image or None
        """
        if self.df is None:
            logger.error("No DataFrame available for chart generation")
            return None
        
        try:
            chart_type = chart_spec.get('type', 'bar')
            x_col = chart_spec.get('x_col')
            y_col = chart_spec.get('y_col')
            title = chart_spec.get('title', 'Data Visualization')
            x_label = chart_spec.get('x_label', x_col)
            y_label = chart_spec.get('y_label', y_col)
            
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if chart_type == 'bar' and x_col and y_col:
                x_data = self.df[x_col].to_list()
                y_data = self.df[y_col].cast(pl.Float64, strict=False).to_list()
                ax.bar(x_data, y_data)
                ax.set_xlabel(x_label if x_label else x_col)
                ax.set_ylabel(y_label if y_label else y_col)
                
            elif chart_type == 'line' and x_col and y_col:
                x_data = self.df[x_col].to_list()
                y_data = self.df[y_col].cast(pl.Float64, strict=False).to_list()
                ax.plot(x_data, y_data, marker='o')
                ax.set_xlabel(x_label if x_label else x_col)
                ax.set_ylabel(y_label if y_label else y_col)
                
            elif chart_type == 'scatter' and x_col and y_col:
                x_data = self.df[x_col].cast(pl.Float64, strict=False).to_list()
                y_data = self.df[y_col].cast(pl.Float64, strict=False).to_list()
                ax.scatter(x_data, y_data)
                ax.set_xlabel(x_label if x_label else x_col)
                ax.set_ylabel(y_label if y_label else y_col)
                
            elif chart_type == 'pie' and y_col:
                labels = self.df[x_col].to_list() if x_col else None
                values = self.df[y_col].cast(pl.Float64, strict=False).to_list()
                ax.pie(values, labels=labels, autopct='%1.1f%%')
                
            elif chart_type == 'hist' and y_col:
                data = self.df[y_col].cast(pl.Float64, strict=False).to_list()
                ax.hist(data, bins=20)
                ax.set_xlabel(y_label if y_label else y_col)
                ax.set_ylabel('Frequency')
            
            ax.set_title(title)
            plt.tight_layout()
            
            # Save to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close(fig)
            
            logger.info(f"Generated {chart_type} chart for session {self.session_id}")
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Error generating chart: {e}", exc_info=True)
            return None
    
    def add_conversation(self, role: str, content: str):
        """Add to conversation history"""
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
    def touch(self):
        """Update last accessed time"""
        self.last_accessed = datetime.now()
        
    def close(self):
        """Cleanup session resources"""
        self.df = None
        self.image_data = None
        logger.info(f"Closed session {self.session_id}")


class SessionManager:
    """Manages all analysis sessions"""
    
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[str, AnalysisSession] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.lock = threading.Lock()
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
    def create_session(self, data: Dict[str, Any], url: str) -> str:
        """Create a new session and return session ID"""
        session_id = str(uuid.uuid4())
        
        try:
            session = AnalysisSession(session_id, data, url)
            
            with self.lock:
                self.sessions[session_id] = session
                
            logger.info(f"Created session {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
            
    def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        """Get session by ID"""
        with self.lock:
            logger.info(f"Looking up session: {session_id}")
            logger.info(f"Active sessions: {list(self.sessions.keys())}")
            session = self.sessions.get(session_id)
            if session:
                session.touch()
                logger.info(f"Session found: {session_id}, last_accessed updated")
            else:
                logger.warning(f"Session not found: {session_id}")
            return session
            
    def end_session(self, session_id: str):
        """End a session and cleanup resources"""
        with self.lock:
            session = self.sessions.pop(session_id, None)
            if session:
                session.close()
                logger.info(f"Ended session {session_id}")
                
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired = []
        
        with self.lock:
            for session_id, session in self.sessions.items():
                if now - session.last_accessed > self.session_timeout:
                    expired.append(session_id)
                    
        for session_id in expired:
            self.end_session(session_id)
            logger.info(f"Cleaned up expired session {session_id}")
            
    def _start_cleanup_thread(self):
        """Start background thread for session cleanup"""
        def cleanup_loop():
            import time
            while True:
                time.sleep(300)  # Check every 5 minutes
                self.cleanup_expired_sessions()
                
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
        logger.info("Started session cleanup thread")


# Global session manager instance
session_manager = SessionManager(session_timeout_minutes=30)
