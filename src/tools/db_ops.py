"""
PostgreSQL AI Agent MVP - Database Operations Tools
MCP Server 1: Core database interactions and query execution
"""

import psycopg2
import psycopg2.extras
from typing import Dict, Any, List, Optional
import logging
import os
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseOperations:
    """Database operations handler for PostgreSQL"""
    
    def __init__(self):
        """Initialize database operations"""
        self.connection_string = os.getenv("DATABASE_URL")
        if not self.connection_string:
            logger.warning("DATABASE_URL not set, using default connection parameters")
            self.connection_string = "postgresql://postgres:password@localhost:5432/postgres"
        else:
            logger.info("DATABASE_URL loaded from environment")
        
        logger.info("DatabaseOperations initialized")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    async def execute_select_query(self, sql_query: str, limit: int = 1000) -> Dict[str, Any]:
        """
        Execute a SELECT query safely and return results
        
        Args:
            sql_query: SQL SELECT query to execute
            limit: Maximum number of rows to return (default 1000)
            
        Returns:
            Dict containing query results, metadata, and execution stats
        """
        try:
            logger.info(f"Executing SELECT query: {sql_query[:100]}...")
            
            # Basic validation - ensure it's a SELECT query
            query_upper = sql_query.strip().upper()
            if not query_upper.startswith('SELECT'):
                return {
                    "status": "error",
                    "message": "Only SELECT queries are allowed in this function",
                    "query": sql_query
                }
            
            # Check for potentially dangerous operations
            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
            if any(keyword in query_upper for keyword in dangerous_keywords):
                return {
                    "status": "error",
                    "message": "Query contains potentially dangerous operations",
                    "query": sql_query
                }
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Add LIMIT if not present and limit is specified
                    if limit and 'LIMIT' not in query_upper:
                        sql_query += f" LIMIT {limit}"
                    
                    # Execute the query
                    cursor.execute(sql_query)
                    
                    # Fetch results
                    rows = cursor.fetchall()
                    
                    # Convert to list of dictionaries
                    results = [dict(row) for row in rows]
                    
                    # Get column information
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    
                    response = {
                        "status": "success",
                        "data": results,
                        "metadata": {
                            "row_count": len(results),
                            "columns": columns,
                            "query": sql_query,
                            "limited": limit and len(results) == limit
                        }
                    }
                    
                    logger.info(f"Query executed successfully, returned {len(results)} rows")
                    return response
                    
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error: {e}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}",
                "query": sql_query,
                "error_type": "database_error"
            }
        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}")
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "query": sql_query,
                "error_type": "system_error"
            }
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test database connection
        
        Returns:
            Dict containing connection status
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()[0]
                    
                    return {
                        "status": "success",
                        "message": "Database connection successful",
                        "database_version": version
                    }
                    
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return {
                "status": "error",
                "message": f"Database connection failed: {str(e)}",
                "error_type": "connection_error"
            }

# Global instance
db_ops = DatabaseOperations()

# Convenience functions for tools
async def execute_select_query(sql_query: str, limit: int = 1000) -> Dict[str, Any]:
    """Execute a SELECT query - tool function"""
    return await db_ops.execute_select_query(sql_query, limit)

async def test_database_connection() -> Dict[str, Any]:
    """Test database connection - tool function"""
    return await db_ops.test_connection() 