"""
PostgreSQL AI Agent MVP - Database Operations Tools
MCP Server 1: Core database interactions and query execution
"""

import psycopg2
import psycopg2.extras
from typing import Dict, Any, List, Optional
import logging
import os
import json
from datetime import datetime, date
from decimal import Decimal
from contextlib import contextmanager
from dotenv import load_dotenv
from utils.redis_client import get_redis_client

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

def serialize_for_json(obj):
    """
    Custom JSON serializer for database objects
    Handles datetime, date, Decimal, and other non-serializable types
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, '__dict__'):
        return str(obj)
    else:
        return str(obj)

def make_json_serializable(data):
    """
    Recursively convert data to be JSON serializable
    """
    if isinstance(data, dict):
        return {key: make_json_serializable(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [make_json_serializable(item) for item in data]
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    elif isinstance(data, Decimal):
        return float(data)
    elif data is None:
        return None
    elif isinstance(data, (str, int, float, bool)):
        return data
    else:
        return str(data)

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
        Fetch enhanced database schema context with intelligent entity mapping
        Includes Redis caching with 1-hour TTL to reduce database load
        
        Args:
            table_names: Optional list of specific tables to fetch (if None, fetches all)
            include_samples: Whether to include sample data from tables
            
        Returns:
            Dict containing enhanced schema structure with entity mapping and semantic context
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
            
            logger.info(f"Fetching enhanced schema context from database for tables: {table_names or 'all'}")
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    schema_context = {
                        "tables": {},
                        "relationships": [],
                        "entity_mappings": {},  # NEW: Intelligent entity mapping
                        "semantic_context": {},  # NEW: Semantic understanding
                        "column_value_analysis": {},  # NEW: Column value patterns
                        "natural_language_guide": {},  # NEW: AI guidance
                        "indexes": {},
                        "constraints": {},
                        "metadata": {
                            "total_tables": 0,
                            "include_samples": include_samples,
                            "filtered_tables": table_names,
                            "cached": False,
                            "cache_key": cache_key,
                            "enhanced_schema": True
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
                                "foreign_keys": [],
                                "description": f"Table containing {table_name} data",
                                "estimated_rows": 0
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
                    
                    # NEW: Enhanced Analysis - Column Value Analysis
                    await self._analyze_column_values(cursor, schema_context, table_filter, params)
                    
                    # NEW: Build Entity Mappings
                    await self._build_entity_mappings(schema_context)
                    
                    # NEW: Create Semantic Context
                    await self._create_semantic_context(schema_context)
                    
                    # NEW: Generate Natural Language Guide
                    await self._generate_natural_language_guide(schema_context)
                    
                    # Include sample data if requested
                    if include_samples:
                        schema_context["samples"] = {}
                        for table_name in schema_context["tables"].keys():
                            try:
                                sample_query = f"SELECT * FROM {table_name} LIMIT 3"
                                cursor.execute(sample_query)
                                sample_rows = cursor.fetchall()
                                schema_context["samples"][table_name] = [make_json_serializable(dict(row)) for row in sample_rows]
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
                            logger.info(f"Enhanced schema cached successfully with key: {cache_key}")
                    
                    logger.info(f"Enhanced schema context fetched successfully for {len(schema_context['tables'])} tables with entity mappings")
                    
                    return {
                        "status": "success",
                        "schema_context": schema_context,
                        "message": f"Enhanced schema fetched from database for {len(schema_context['tables'])} tables",
                        "cached": False
                    }
                    
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error fetching enhanced schema: {e}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}",
                "error_type": "database_error"
            }
        except Exception as e:
            logger.error(f"Unexpected error fetching enhanced schema: {e}")
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "error_type": "system_error"
            }

    async def _analyze_column_values(self, cursor, schema_context: Dict[str, Any], table_filter: str, params: List[str]):
        """Analyze column values to understand data patterns and possible values"""
        for table_name, table_info in schema_context["tables"].items():
            try:
                # Get row count
                cursor.execute(f"SELECT COUNT(*) as row_count FROM {table_name}")
                row_count = cursor.fetchone()['row_count']
                schema_context["tables"][table_name]["estimated_rows"] = row_count
                
                # Analyze specific columns for patterns
                for column_name, column_info in table_info["columns"].items():
                    column_analysis = {
                        "unique_values": [],
                        "sample_values": [],
                        "value_patterns": [],
                        "is_categorical": False,
                        "semantic_type": self._infer_semantic_type(column_name, column_info["data_type"])
                    }
                    
                    # For text columns with limited unique values, get all possible values
                    if column_info["data_type"] in ["text", "varchar", "character varying"] and row_count < 10000:
                        try:
                            cursor.execute(f"""
                                SELECT DISTINCT {column_name} as value, COUNT(*) as count 
                                FROM {table_name} 
                                WHERE {column_name} IS NOT NULL 
                                GROUP BY {column_name} 
                                ORDER BY count DESC 
                                LIMIT 20
                            """)
                            values = cursor.fetchall()
                            
                            if len(values) <= 10:  # Likely categorical
                                column_analysis["is_categorical"] = True
                                column_analysis["unique_values"] = [row['value'] for row in values]
                            else:
                                column_analysis["sample_values"] = [row['value'] for row in values[:5]]
                                
                        except Exception as e:
                            logger.debug(f"Could not analyze values for {table_name}.{column_name}: {e}")
                    
                    # Store analysis
                    if table_name not in schema_context["column_value_analysis"]:
                        schema_context["column_value_analysis"][table_name] = {}
                    schema_context["column_value_analysis"][table_name][column_name] = column_analysis
                    
            except Exception as e:
                logger.debug(f"Could not analyze table {table_name}: {e}")

    async def _build_entity_mappings(self, schema_context: Dict[str, Any]):
        """Build intelligent entity mappings for natural language understanding"""
        entity_mappings = {}
        
        for table_name, table_info in schema_context["tables"].items():
            # Table-level mappings
            table_mappings = {
                "table_name": table_name,
                "possible_entities": [table_name],
                "column_mappings": {}
            }
            
            # Add plural/singular variations
            if table_name.endswith('s'):
                table_mappings["possible_entities"].append(table_name[:-1])  # users -> user
            else:
                table_mappings["possible_entities"].append(table_name + 's')  # user -> users
            
            # Analyze columns for entity mappings
            for column_name, column_info in table_info["columns"].items():
                column_mappings = {
                    "column_name": column_name,
                    "data_type": column_info["data_type"],
                    "semantic_type": schema_context["column_value_analysis"].get(table_name, {}).get(column_name, {}).get("semantic_type", "unknown"),
                    "possible_filters": []
                }
                
                # Special handling for categorical columns
                if schema_context["column_value_analysis"].get(table_name, {}).get(column_name, {}).get("is_categorical"):
                    unique_values = schema_context["column_value_analysis"][table_name][column_name]["unique_values"]
                    column_mappings["categorical_values"] = unique_values
                    
                    # Create entity mappings for categorical values
                    if column_name == "role" and unique_values:
                        for value in unique_values:
                            if value:  # Skip None values
                                # Map "clients" -> "users WHERE role = 'client'"
                                entity_key = f"{value}s" if not value.endswith('s') else value
                                if entity_key not in entity_mappings:
                                    entity_mappings[entity_key] = []
                                entity_mappings[entity_key].append({
                                    "table": table_name,
                                    "filter_condition": f"{column_name} = '{value}'",
                                    "description": f"All {value}s from {table_name} table"
                                })
                                
                                # Also map singular form
                                singular_key = value
                                if singular_key not in entity_mappings:
                                    entity_mappings[singular_key] = []
                                entity_mappings[singular_key].append({
                                    "table": table_name,
                                    "filter_condition": f"{column_name} = '{value}'",
                                    "description": f"All {value}s from {table_name} table"
                                })
                
                table_mappings["column_mappings"][column_name] = column_mappings
            
            entity_mappings[table_name] = [table_mappings]
        
        schema_context["entity_mappings"] = entity_mappings

    async def _create_semantic_context(self, schema_context: Dict[str, Any]):
        """Create semantic context for better AI understanding"""
        semantic_context = {
            "table_purposes": {},
            "common_queries": {},
            "relationship_descriptions": []
        }
        
        # Analyze table purposes based on columns
        for table_name, table_info in schema_context["tables"].items():
            columns = list(table_info["columns"].keys())
            
            # Infer table purpose
            purpose = f"Stores {table_name} information"
            if "email" in columns and "password" in [col for col in columns if "password" in col.lower()]:
                purpose = f"User authentication and profile data"
            elif "created_at" in columns or "updated_at" in columns:
                purpose = f"Transactional data with timestamps"
            
            semantic_context["table_purposes"][table_name] = purpose
            
            # Generate common query patterns
            common_queries = []
            if "status" in columns:
                common_queries.append(f"active {table_name}")
                common_queries.append(f"inactive {table_name}")
            if "role" in columns:
                common_queries.append(f"{table_name} by role")
            if "created_at" in columns:
                common_queries.append(f"recent {table_name}")
                common_queries.append(f"{table_name} created today")
            
            semantic_context["common_queries"][table_name] = common_queries
        
        # Describe relationships
        for rel in schema_context["relationships"]:
            description = f"{rel['source_table']}.{rel['source_column']} references {rel['target_table']}.{rel['target_column']}"
            semantic_context["relationship_descriptions"].append(description)
        
        schema_context["semantic_context"] = semantic_context

    async def _generate_natural_language_guide(self, schema_context: Dict[str, Any]):
        """Generate natural language guide for AI"""
        guide = {
            "available_tables": list(schema_context["tables"].keys()),
            "entity_resolution": {},
            "query_examples": {},
            "important_notes": []
        }
        
        # Entity resolution guide
        for entity, mappings in schema_context["entity_mappings"].items():
            if isinstance(mappings, list) and len(mappings) > 0:
                first_mapping = mappings[0]
                if isinstance(first_mapping, dict) and "filter_condition" in first_mapping:
                    guide["entity_resolution"][entity] = {
                        "maps_to": f"SELECT * FROM {first_mapping['table']} WHERE {first_mapping['filter_condition']}",
                        "description": first_mapping.get("description", "")
                    }
        
        # Query examples
        for table_name in schema_context["tables"].keys():
            examples = [
                f"show me all {table_name}",
                f"get {table_name} data",
                f"list {table_name}"
            ]
            
            # Add status-based examples if status column exists
            if "status" in schema_context["tables"][table_name]["columns"]:
                examples.extend([
                    f"show me active {table_name}",
                    f"find inactive {table_name}"
                ])
            
            guide["query_examples"][table_name] = examples
        
        # Important notes
        guide["important_notes"] = [
            "Always use existing table names from the available_tables list",
            "Use entity_resolution mappings to convert conceptual entities to actual SQL",
            "Check column_value_analysis for categorical column values",
            "Consider relationships when joining tables"
        ]
        
        schema_context["natural_language_guide"] = guide

    def _infer_semantic_type(self, column_name: str, data_type: str) -> str:
        """Infer semantic type from column name and data type"""
        column_lower = column_name.lower()
        
        if "email" in column_lower:
            return "email"
        elif "phone" in column_lower:
            return "phone"
        elif "password" in column_lower:
            return "password"
        elif "status" in column_lower:
            return "status"
        elif "role" in column_lower:
            return "role"
        elif "created_at" in column_lower or "updated_at" in column_lower:
            return "timestamp"
        elif "id" in column_lower:
            return "identifier"
        elif "name" in column_lower:
            return "name"
        elif data_type in ["timestamp", "timestamptz", "date"]:
            return "datetime"
        elif data_type in ["integer", "bigint", "smallint"]:
            return "numeric"
        elif data_type in ["text", "varchar", "character varying"]:
            return "text"
        else:
            return "unknown"

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
                    
                    # Convert to list of dictionaries and make JSON serializable
                    results = [make_json_serializable(dict(row)) for row in rows]
                    
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