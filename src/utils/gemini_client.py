"""
PostgreSQL AI Agent MVP - Gemini API Client Utility
"""

import google.generativeai as genai
import os
import json
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class GeminiClient:
    """Utility class for Gemini API operations"""
    
    def __init__(self):
        """Initialize Gemini client"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model - using gemini-2.0-flash as per user's API
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        logger.info("GeminiClient initialized with gemini-2.0-flash model")
    
    async def generate_content(self, prompt: str) -> str:
        """
        Generate content using Gemini API
        
        Args:
            prompt: The prompt to send to Gemini
            
        Returns:
            Generated text response
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating content with Gemini: {e}")
            raise
    
    async def extract_intent(self, query: str) -> Dict[str, Any]:
        """
        Extract intent from user query using Gemini
        
        Args:
            query: User's natural language query
            
        Returns:
            Dictionary with intent information
        """
        prompt = f"""
        Analyze this database query and return a JSON object with the following structure:
        {{
            "intent": "SELECT|UPDATE|DELETE|INSERT|UNKNOWN",
            "confidence": 0.0-1.0,
            "keywords": ["list", "of", "relevant", "keywords"],
            "table_mentioned": "table_name or null",
            "operation_type": "READ|WRITE|UNKNOWN"
        }}
        
        Query: "{query}"
        
        Return only the JSON object, no additional text.
        """
        
        try:
            response = await self.generate_content(prompt)
            
            # Try to parse JSON from response
            # Remove any markdown formatting
            json_text = response.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:]
            if json_text.endswith('```'):
                json_text = json_text[:-3]
            json_text = json_text.strip()
            
            intent_data = json.loads(json_text)
            
            # Validate required fields
            required_fields = ['intent', 'confidence', 'keywords']
            for field in required_fields:
                if field not in intent_data:
                    logger.warning(f"Missing field {field} in intent extraction")
                    intent_data[field] = self._get_default_value(field)
            
            return intent_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            logger.error(f"Raw response: {response}")
            
            # Return fallback intent
            return {
                "intent": "UNKNOWN",
                "confidence": 0.0,
                "keywords": [],
                "table_mentioned": None,
                "operation_type": "UNKNOWN"
            }
        except Exception as e:
            logger.error(f"Error extracting intent: {e}")
            raise
    
    async def build_sql_query(self, intent_data: Dict[str, Any], schema_context: str) -> str:
        """
        Build SQL query from intent and schema context
        
        Args:
            intent_data: Intent information from extract_intent
            schema_context: Database schema information
            
        Returns:
            Generated SQL query
        """
        prompt = f"""
        Generate a PostgreSQL query based on the following information:
        
        Intent: {intent_data}
        Database Schema: {schema_context}
        
        Requirements:
        1. Generate only valid PostgreSQL syntax
        2. Use proper table and column names from the schema
        3. Include appropriate WHERE clauses if needed
        4. For SELECT queries, limit results to 1000 rows unless specified otherwise
        5. Return only the SQL query, no additional text or formatting
        
        SQL Query:
        """
        
        try:
            response = await self.generate_content(prompt)
            sql_query = response.strip()
            
            # Remove any markdown formatting
            if sql_query.startswith('```sql'):
                sql_query = sql_query[6:]
            if sql_query.startswith('```'):
                sql_query = sql_query[3:]
            if sql_query.endswith('```'):
                sql_query = sql_query[:-3]
            
            return sql_query.strip()
            
        except Exception as e:
            logger.error(f"Error building SQL query: {e}")
            raise
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing fields"""
        defaults = {
            'intent': 'UNKNOWN',
            'confidence': 0.0,
            'keywords': [],
            'table_mentioned': None,
            'operation_type': 'UNKNOWN'
        }
        return defaults.get(field, None)

# Global instance
gemini_client = None

def get_gemini_client() -> GeminiClient:
    """Get or create global Gemini client instance"""
    global gemini_client
    if gemini_client is None:
        gemini_client = GeminiClient()
    return gemini_client 