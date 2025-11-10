"""
Session Manager for Revela
Manages ephemeral analysis sessions with in-memory DuckDB instances
"""

import duckdb
import logging
import threading
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import uuid
from html.parser import HTMLParser
import io

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
    """Represents a single ephemeral analysis session"""
    
    def __init__(self, session_id: str, data: Dict[str, Any], url: str):
        self.session_id = session_id
        self.data = data
        self.url = url
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.db_connection = None
        self.table_name = None
        self.data_type = data.get('type', 'unknown')
        self.conversation_history = []
        
        # Initialize DuckDB connection
        self._initialize_database()
        
    def _initialize_database(self):
        """Initialize in-memory DuckDB instance and load data"""
        try:
            # Create in-memory connection
            self.db_connection = duckdb.connect(':memory:')
            logger.info(f"Created in-memory DuckDB for session {self.session_id}")
            
            # Load data based on type
            if self.data_type == 'table':
                self._load_table_data()
            elif self.data_type in ['image', 'canvas']:
                # For images, we'll store metadata
                self._load_image_metadata()
                
        except Exception as e:
            logger.error(f"Error initializing database for session {self.session_id}: {e}")
            raise
            
    def _load_table_data(self):
        """Parse HTML table and load into DuckDB"""
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
                
            # First row as headers
            headers = table_data[0]
            rows = table_data[1:]
            
            # Clean headers (make them valid SQL identifiers)
            clean_headers = []
            for i, header in enumerate(headers):
                clean_header = header.replace(' ', '_').replace('-', '_')
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
            
            # Create table name
            self.table_name = 'analysis_data'
            
            # Build CREATE TABLE statement (all columns as VARCHAR for simplicity)
            columns_def = ', '.join([f'"{h}" VARCHAR' for h in unique_headers])
            create_sql = f'CREATE TABLE {self.table_name} ({columns_def})'
            
            self.db_connection.execute(create_sql)
            logger.info(f"Created table {self.table_name} with {len(unique_headers)} columns")
            
            # Insert data
            placeholders = ', '.join(['?' for _ in unique_headers])
            insert_sql = f'INSERT INTO {self.table_name} VALUES ({placeholders})'
            
            for row in rows:
                # Pad or truncate row to match header count
                padded_row = row[:len(unique_headers)]
                while len(padded_row) < len(unique_headers):
                    padded_row.append('')
                    
                self.db_connection.execute(insert_sql, padded_row)
            
            logger.info(f"Inserted {len(rows)} rows into {self.table_name}")
            
            # Store schema info
            self.schema_info = {
                'columns': unique_headers,
                'row_count': len(rows),
                'col_count': len(unique_headers)
            }
            
        except Exception as e:
            logger.error(f"Error loading table data: {e}")
            raise
            
    def _load_image_metadata(self):
        """Store image metadata for chart analysis"""
        self.table_name = 'image_metadata'
        
        try:
            self.db_connection.execute('''
                CREATE TABLE image_metadata (
                    key VARCHAR,
                    value VARCHAR
                )
            ''')
            
            # Store metadata
            metadata = [
                ('type', self.data.get('type', 'unknown')),
                ('width', str(self.data.get('width', 0))),
                ('height', str(self.data.get('height', 0))),
                ('alt', self.data.get('alt', '')),
                ('src', self.data.get('src', ''))
            ]
            
            for key, value in metadata:
                self.db_connection.execute(
                    'INSERT INTO image_metadata VALUES (?, ?)',
                    [key, value]
                )
                
            logger.info(f"Stored image metadata for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Error loading image metadata: {e}")
            raise
            
    def get_summary_stats(self) -> Dict[str, Any]:
        """Generate summary statistics for the data"""
        try:
            if self.data_type == 'table' and self.table_name:
                # Get row count
                result = self.db_connection.execute(
                    f'SELECT COUNT(*) as count FROM {self.table_name}'
                ).fetchone()
                row_count = result[0]
                
                # Get column info
                columns = self.db_connection.execute(
                    f'PRAGMA table_info({self.table_name})'
                ).fetchall()
                
                return {
                    'type': 'table',
                    'row_count': row_count,
                    'column_count': len(columns),
                    'columns': [col[1] for col in columns],
                    'sample_rows': self._get_sample_rows(5)
                }
            elif self.data_type in ['image', 'canvas']:
                return {
                    'type': self.data_type,
                    'width': self.data.get('width'),
                    'height': self.data.get('height'),
                    'alt': self.data.get('alt', ''),
                }
        except Exception as e:
            logger.error(f"Error getting summary stats: {e}")
            return {'error': str(e)}
            
    def _get_sample_rows(self, limit: int = 5) -> list:
        """Get sample rows from the table"""
        try:
            result = self.db_connection.execute(
                f'SELECT * FROM {self.table_name} LIMIT {limit}'
            ).fetchall()
            return [list(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting sample rows: {e}")
            return []
            
    def execute_query(self, query: str) -> Any:
        """Execute SQL query on the session data"""
        try:
            result = self.db_connection.execute(query).fetchall()
            return result
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
            
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
        """Close the database connection"""
        if self.db_connection:
            self.db_connection.close()
            logger.info(f"Closed DuckDB connection for session {self.session_id}")


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
            session = self.sessions.get(session_id)
            if session:
                session.touch()
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
