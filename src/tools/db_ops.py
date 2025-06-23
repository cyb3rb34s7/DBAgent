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
from utils.redis_client import get_redis_client

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
        
        # Initialize Redis client for caching
        self.redis_client = get_redis_client()
        
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
    
    async def fetch_schema_context(self, table_names: Optional[List[str]] = None, include_samples: bool = False) -> Dict[str, Any]:
        """
        Fetch database schema context by inspecting PostgreSQL system catalogs
        Includes Redis caching with 1-hour TTL to reduce database load
        
        Args:
            table_names: Optional list of specific tables to fetch (if None, fetches all)
            include_samples: Whether to include sample data from tables
            
        Returns:
            Dict containing schema structure, relationships, and optionally sample data
        """
        try:
            # Generate cache key
            cache_key = self.redis_client.generate_schema_cache_key(table_names, include_samples)
            
            # Try to get from cache first
            if self.redis_client.is_connected():
                cached_schema = self.redis_client.get_cached_schema(cache_key)
                if cached_schema:
                    logger.info(f"Returning cached schema for key: {cache_key}")
                    return {
                        "status": "success",
                        "schema_context": cached_schema,
                        "message": f"Schema fetched from cache for {len(cached_schema.get('tables', {}))} tables",
                        "cached": True
                    }
            
            logger.info(f"Fetching schema context from database for tables: {table_names or 'all'}")
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    schema_context = {
                        "tables": {},
                        "relationships": [],
                        "indexes": {},
                        "constraints": {},
                        "metadata": {
                            "total_tables": 0,
                            "include_samples": include_samples,
                            "filtered_tables": table_names,
                            "cached": False,
                            "cache_key": cache_key
                        }
                    }
                    
                    # Build WHERE clause for table filtering
                    table_filter = ""
                    if table_names:
                        placeholders = ",".join(["%s"] * len(table_names))
                        table_filter = f"AND t.table_name IN ({placeholders})"
                    
                    # Query 1: Get table and column information
                    table_query = f"""
                    SELECT 
                        t.table_name,
                        t.table_type,
                        c.column_name,
                        c.data_type,
                        c.is_nullable,
                        c.column_default,
                        c.character_maximum_length,
                        c.numeric_precision,
                        c.numeric_scale,
                        c.ordinal_position
                    FROM information_schema.tables t
                    JOIN information_schema.columns c ON t.table_name = c.table_name
                    WHERE t.table_schema = 'public' 
                        AND t.table_type = 'BASE TABLE'
                        {table_filter}
                    ORDER BY t.table_name, c.ordinal_position
                    """
                    
                    params = table_names if table_names else []
                    cursor.execute(table_query, params)
                    table_rows = cursor.fetchall()
                    
                    # Process table and column information
                    for row in table_rows:
                        table_name = row['table_name']
                        if table_name not in schema_context["tables"]:
                            schema_context["tables"][table_name] = {
                                "table_type": row['table_type'],
                                "columns": {},
                                "primary_keys": [],
                                "foreign_keys": []
                            }
                        
                        # Add column information
                        schema_context["tables"][table_name]["columns"][row['column_name']] = {
                            "data_type": row['data_type'],
                            "is_nullable": row['is_nullable'] == 'YES',
                            "column_default": row['column_default'],
                            "character_maximum_length": row['character_maximum_length'],
                            "numeric_precision": row['numeric_precision'],
                            "numeric_scale": row['numeric_scale'],
                            "ordinal_position": row['ordinal_position']
                        }
                    
                    # Query 2: Get primary key information
                    pk_query = f"""
                    SELECT 
                        tc.table_name,
                        kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_schema = 'public' 
                        AND tc.constraint_type = 'PRIMARY KEY'
                        {table_filter.replace('t.table_name', 'tc.table_name') if table_filter else ''}
                    ORDER BY tc.table_name, kcu.ordinal_position
                    """
                    
                    cursor.execute(pk_query, params)
                    pk_rows = cursor.fetchall()
                    
                    for row in pk_rows:
                        table_name = row['table_name']
                        if table_name in schema_context["tables"]:
                            schema_context["tables"][table_name]["primary_keys"].append(row['column_name'])
                    
                    # Query 3: Get foreign key relationships
                    fk_query = f"""
                    SELECT 
                        tc.table_name AS source_table,
                        kcu.column_name AS source_column,
                        ccu.table_name AS target_table,
                        ccu.column_name AS target_column,
                        tc.constraint_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu 
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.table_schema = 'public' 
                        AND tc.constraint_type = 'FOREIGN KEY'
                        {table_filter.replace('t.table_name', 'tc.table_name') if table_filter else ''}
                    ORDER BY tc.table_name, kcu.ordinal_position
                    """
                    
                    cursor.execute(fk_query, params)
                    fk_rows = cursor.fetchall()
                    
                    for row in fk_rows:
                        source_table = row['source_table']
                        if source_table in schema_context["tables"]:
                            fk_info = {
                                "constraint_name": row['constraint_name'],
                                "source_column": row['source_column'],
                                "target_table": row['target_table'],
                                "target_column": row['target_column']
                            }
                            schema_context["tables"][source_table]["foreign_keys"].append(fk_info)
                            
                            # Also add to relationships list
                            schema_context["relationships"].append({
                                "type": "foreign_key",
                                "source_table": source_table,
                                "source_column": row['source_column'],
                                "target_table": row['target_table'],
                                "target_column": row['target_column'],
                                "constraint_name": row['constraint_name']
                            })
                    
                    # Query 4: Get index information
                    index_query = f"""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                        {table_filter.replace('t.table_name', 'tablename') if table_filter else ''}
                    ORDER BY tablename, indexname
                    """
                    
                    cursor.execute(index_query, params)
                    index_rows = cursor.fetchall()
                    
                    for row in index_rows:
                        table_name = row['tablename']
                        if table_name not in schema_context["indexes"]:
                            schema_context["indexes"][table_name] = []
                        
                        schema_context["indexes"][table_name].append({
                            "index_name": row['indexname'],
                            "definition": row['indexdef']
                        })
                    
                    # Query 5: Get sample data if requested
                    if include_samples:
                        schema_context["samples"] = {}
                        for table_name in schema_context["tables"].keys():
                            try:
                                sample_query = f"SELECT * FROM {table_name} LIMIT 3"
                                cursor.execute(sample_query)
                                sample_rows = cursor.fetchall()
                                schema_context["samples"][table_name] = [dict(row) for row in sample_rows]
                            except Exception as e:
                                logger.warning(f"Could not fetch samples for table {table_name}: {e}")
                                schema_context["samples"][table_name] = []
                    
                    # Update metadata
                    schema_context["metadata"]["total_tables"] = len(schema_context["tables"])
                    
                    # Cache the result for 1 hour (3600 seconds)
                    if self.redis_client.is_connected():
                        cache_success = self.redis_client.cache_schema(cache_key, schema_context, ttl_seconds=3600)
                        schema_context["metadata"]["cached"] = cache_success
                        if cache_success:
                            logger.info(f"Schema cached successfully with key: {cache_key}")
                    
                    logger.info(f"Schema context fetched successfully for {len(schema_context['tables'])} tables")
                    
                    return {
                        "status": "success",
                        "schema_context": schema_context,
                        "message": f"Schema fetched from database for {len(schema_context['tables'])} tables",
                        "cached": False
                    }
                    
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error fetching schema: {e}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}",
                "error_type": "database_error"
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching schema: {e}")
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "error_type": "system_error"
            }

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

async def fetch_schema_context(table_names: Optional[List[str]] = None, include_samples: bool = False) -> Dict[str, Any]:
    """Fetch database schema context - tool function"""
    return await db_ops.fetch_schema_context(table_names, include_samples)

async def validate_query(sql_query: str) -> Dict[str, Any]:
    """
    Validate SQL query for basic syntax and safety
    
    Args:
        sql_query: SQL query to validate
        
    Returns:
        Dict containing validation results
    """
    from agents.query_builder import get_query_builder
    
    query_builder = get_query_builder()
    return await query_builder.validate_query(sql_query)

async def build_sql_query(intent_data: Dict[str, Any], table_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Build SQL query from intent using Gemini AI and schema context
    
    Args:
        intent_data: Intent information from extract_intent
        table_names: Optional list of specific tables to include
        
    Returns:
        Dict containing generated SQL and metadata
    """
    from agents.query_builder import get_query_builder
    
    query_builder = get_query_builder()
    return await query_builder.build_sql_query(intent_data, table_names)

async def test_database_connection() -> Dict[str, Any]:
    """Test database connection - tool function"""
    return await db_ops.test_connection() 