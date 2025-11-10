"""
LLM Code Executor for Revela
Safely executes LLM-generated Polars queries and chart generation code
"""

import logging
import json
import re
from typing import Dict, Any, Optional
import polars as pl

logger = logging.getLogger(__name__)


class CodeExecutor:
    """Safely execute LLM-generated data analysis code"""
    
    def __init__(self, session):
        """
        Args:
            session: AnalysisSession instance with DataFrame
        """
        self.session = session
        self.df = session.df
        
    def parse_llm_response_for_code(self, llm_response: str) -> Dict[str, Any]:
        """
        Parse LLM response to extract code blocks and chart specifications.
        
        Args:
            llm_response: Full text response from LLM
            
        Returns:
            Dictionary with parsed code, chart specs, and explanation
        """
        result = {
            'has_code': False,
            'has_chart': False,
            'polars_code': None,
            'chart_spec': None,
            'explanation': llm_response
        }
        
        # Extract Python code blocks
        code_pattern = r'```python\n(.*?)```'
        code_matches = re.findall(code_pattern, llm_response, re.DOTALL)
        
        if code_matches:
            result['has_code'] = True
            result['polars_code'] = code_matches[0].strip()
        
        # Extract JSON chart specifications
        chart_pattern = r'```json\n(.*?)```'
        chart_matches = re.findall(chart_pattern, llm_response, re.DOTALL)
        
        if chart_matches:
            try:
                chart_spec = json.loads(chart_matches[0].strip())
                if 'type' in chart_spec:  # Validate it's a chart spec
                    result['has_chart'] = True
                    result['chart_spec'] = chart_spec
            except json.JSONDecodeError:
                logger.warning("Failed to parse chart specification JSON")
        
        return result
    
    def execute_polars_code(self, code: str) -> Dict[str, Any]:
        """
        Safely execute Polars query code.
        
        Args:
            code: Polars code string to execute
            
        Returns:
            Dictionary with execution results or error
        """
        if self.df is None:
            return {'error': 'No DataFrame available'}
        
        try:
            # Clean up the code - remove import statements since we provide pl and df
            code_lines = code.split('\n')
            cleaned_lines = []
            for line in code_lines:
                # Skip import statements
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    continue
                # Skip empty lines
                if not line.strip():
                    continue
                cleaned_lines.append(line)
            
            code = '\n'.join(cleaned_lines)
            logger.info(f"Cleaned code to execute: {code}")
            
            # Create safe execution environment
            safe_globals = {
                'pl': pl,
                'df': self.df,
                '__builtins__': {
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'len': len,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'sum': sum,
                    'max': max,
                    'min': min,
                    'round': round,
                    'sorted': sorted,
                    'enumerate': enumerate,
                    'range': range,
                    'zip': zip,
                    'True': True,
                    'False': False,
                    'None': None,
                }
            }
            
            # Execute code
            local_vars = {}
            exec(code, safe_globals, local_vars)
            
            # Get result DataFrame or value
            result_df = local_vars.get('result', None)
            
            if isinstance(result_df, pl.DataFrame):
                return {
                    'success': True,
                    'type': 'dataframe',
                    'data': result_df.head(100).to_dicts(),  # Limit to 100 rows
                    'shape': {'rows': result_df.height, 'columns': result_df.width},
                    'columns': result_df.columns
                }
            elif result_df is not None:
                return {
                    'success': True,
                    'type': 'value',
                    'data': str(result_df)
                }
            else:
                return {'error': 'No result variable found in executed code'}
                
        except Exception as e:
            logger.error(f"Error executing Polars code: {e}", exc_info=True)
            return {'error': f'Execution error: {str(e)}'}
    
    def generate_query_prompt(self, user_question: str, df_summary: Dict[str, Any]) -> str:
        """
        Generate prompt for LLM to create Polars query code.
        
        Args:
            user_question: User's data question
            df_summary: DataFrame summary statistics
            
        Returns:
            Formatted prompt for LLM
        """
        prompt = f"""You are a data analysis assistant. The user has asked a question about their data.

**Dataset Information:**
- Rows: {df_summary.get('row_count', 0)}
- Columns: {', '.join(df_summary.get('columns', []))}

**Column Data Types:**
{json.dumps(df_summary.get('dtypes', {}), indent=2)}

**Sample Data (first 5 rows):**
{json.dumps(df_summary.get('sample_rows', []), indent=2)}

**User Question:**
{user_question}

**Instructions:**
1. Analyze the question and determine if it requires data manipulation
2. If yes, write Polars code to answer the question
3. Store the result in a variable called `result`
4. If a chart would help visualize the answer, provide chart specifications in JSON format

**Polars Code Format:**
```python
# Your Polars code here using the 'df' DataFrame
result = df.filter(...).select(...).group_by(...)
```

**Chart Specification Format (if needed):**
```json
{{
  "type": "bar|line|scatter|pie|hist",
  "x_col": "column_name",
  "y_col": "column_name",
  "title": "Chart Title"
}}
```

**Example Response:**
To find the average age by department, I'll group the data:

```python
result = df.group_by('department').agg(pl.col('age').mean().alias('avg_age'))
```

This shows the average age is highest in Engineering.

```json
{{
  "type": "bar",
  "x_col": "department",
  "y_col": "avg_age",
  "title": "Average Age by Department"
}}
```

Now answer the user's question:"""
        
        return prompt


def create_chart_prompt(user_request: str, df_summary: Dict[str, Any]) -> str:
    """
    Create prompt for LLM to suggest chart specifications.
    
    Args:
        user_request: User's chart request
        df_summary: DataFrame summary
        
    Returns:
        Prompt for LLM
    """
    return f"""The user wants to create a chart for their data.

**Dataset Columns:** {', '.join(df_summary.get('columns', []))}

**User Request:** {user_request}

Suggest an appropriate chart and provide the specification in this JSON format:

```json
{{
  "type": "bar|line|scatter|pie|hist",
  "x_col": "column_name",
  "y_col": "column_name",
  "title": "Chart Title"
}}
```

Choose the chart type that best suits the data and user's request."""
