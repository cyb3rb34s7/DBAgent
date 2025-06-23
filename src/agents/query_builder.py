"""
PostgreSQL AI Agent MVP - Query Builder Agent
Agent 2: SQL generation and optimization specialist
"""

import logging
from typing import Dict, Any, List, Optional
from utils.gemini_client import get_gemini_client
from tools.db_ops import fetch_schema_context

logger = logging.getLogger(__name__)

class QueryBuilderAgent:
    """
    Query Builder Agent: SQL generation and optimization specialist
    
    Responsibilities:
    - Natural language to SQL translation
    - Schema context integration for table/column mapping
    - Complex JOIN operations and query optimization
    - Query validation and syntax checking
    - Alternative query generation for complex requests
    - Performance optimization suggestions
    """
    
    def __init__(self):
        """Initialize Query Builder Agent"""
        self.gemini_client = get_gemini_client()
        logger.info("QueryBuilderAgent initialized")
    
    async def build_sql_query(self, intent_data: Dict[str, Any], table_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Build SQL query from intent and schema context using Gemini AI
        
        Args:
            intent_data: Intent information from extract_intent
            table_names: Optional list of specific tables to include in schema context
            
        Returns:
            Dict containing generated SQL, alternatives, and metadata
        """
        try:
            logger.info(f"Building SQL query for intent: {intent_data.get('intent', 'UNKNOWN')}")
            
            # Step 1: Get schema context
            schema_result = await fetch_schema_context(table_names=table_names, include_samples=False)
            
            if schema_result.get('status') != 'success':
                return {
                    "status": "error",
                    "message": f"Failed to fetch schema context: {schema_result.get('message')}",
                    "error_type": "schema_error"
                }
            
            schema_context = schema_result.get('schema_context', {})
            
            # Step 2: Format schema context for Gemini
            formatted_schema = self._format_schema_for_llm(schema_context, intent_data)
            
            # Step 3: Generate SQL using Gemini
            sql_query = await self.gemini_client.build_sql_query(intent_data, formatted_schema)
            
            # Step 4: Validate the generated query
            validation_result = await self.validate_query(sql_query)
            
            # Step 5: Generate alternatives if requested or if validation failed
            alternatives = []
            if not validation_result.get('is_valid', False) or intent_data.get('confidence', 0) < 0.8:
                alternatives = await self._generate_alternative_queries(intent_data, formatted_schema)
            
            return {
                "status": "success",
                "sql_query": sql_query,
                "validation": validation_result,
                "alternatives": alternatives,
                "schema_used": {
                    "tables_count": len(schema_context.get('tables', {})),
                    "relationships_count": len(schema_context.get('relationships', [])),
                    "cached": schema_result.get('cached', False)
                },
                "intent_data": intent_data
            }
            
        except Exception as e:
            logger.error(f"Error building SQL query: {e}")
            return {
                "status": "error",
                "message": f"Failed to build SQL query: {str(e)}",
                "error_type": "build_error"
            }
    
    async def validate_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Validate SQL query for syntax and semantic correctness
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            Dict containing validation results and suggestions
        """
        try:
            logger.info("Validating SQL query")
            
            validation_result = {
                "is_valid": True,
                "issues": [],
                "suggestions": [],
                "query_type": "UNKNOWN",
                "complexity": "SIMPLE"
            }
            
            # Basic syntax checks
            query_upper = sql_query.strip().upper()
            
            # Check if query is empty
            if not sql_query.strip():
                validation_result["is_valid"] = False
                validation_result["issues"].append("Query is empty")
                return validation_result
            
            # Determine query type
            if query_upper.startswith('SELECT'):
                validation_result["query_type"] = "SELECT"
            elif query_upper.startswith('UPDATE'):
                validation_result["query_type"] = "UPDATE"
            elif query_upper.startswith('DELETE'):
                validation_result["query_type"] = "DELETE"
            elif query_upper.startswith('INSERT'):
                validation_result["query_type"] = "INSERT"
            else:
                validation_result["is_valid"] = False
                validation_result["issues"].append("Unsupported query type")
                return validation_result
            
            # Basic syntax validation
            if validation_result["query_type"] == "SELECT":
                if 'FROM' not in query_upper:
                    validation_result["issues"].append("SELECT query missing FROM clause")
                    validation_result["suggestions"].append("Add FROM clause with table name")
            
            # Check for dangerous operations in SELECT queries
            dangerous_keywords = ['DROP', 'TRUNCATE', 'ALTER', 'CREATE']
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    validation_result["is_valid"] = False
                    validation_result["issues"].append(f"Dangerous operation detected: {keyword}")
            
            # Determine complexity
            complexity_indicators = ['JOIN', 'UNION', 'SUBQUERY', 'WITH', 'WINDOW', 'GROUP BY', 'HAVING']
            complexity_count = sum(1 for indicator in complexity_indicators if indicator in query_upper)
            
            if complexity_count == 0:
                validation_result["complexity"] = "SIMPLE"
            elif complexity_count <= 2:
                validation_result["complexity"] = "MEDIUM"
            else:
                validation_result["complexity"] = "COMPLEX"
            
            # Additional suggestions
            if 'LIMIT' not in query_upper and validation_result["query_type"] == "SELECT":
                validation_result["suggestions"].append("Consider adding LIMIT clause for large result sets")
            
            # Mark as invalid if there are critical issues
            if validation_result["issues"]:
                validation_result["is_valid"] = False
            
            logger.info(f"Query validation completed: {validation_result['is_valid']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating query: {e}")
            return {
                "is_valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "suggestions": [],
                "query_type": "UNKNOWN",
                "complexity": "UNKNOWN"
            }
    
    async def optimize_query(self, sql_query: str, schema_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide query optimization suggestions
        
        Args:
            sql_query: SQL query to optimize
            schema_context: Database schema context
            
        Returns:
            Dict containing optimization suggestions
        """
        try:
            logger.info("Analyzing query for optimization opportunities")
            
            optimizations = {
                "suggestions": [],
                "performance_tips": [],
                "index_recommendations": [],
                "rewritten_query": None
            }
            
            query_upper = sql_query.strip().upper()
            
            # Check for missing indexes on commonly filtered columns
            # This is a simplified version - in production, you'd analyze query plans
            if 'WHERE' in query_upper:
                optimizations["suggestions"].append("Ensure indexes exist on WHERE clause columns")
            
            if 'ORDER BY' in query_upper:
                optimizations["suggestions"].append("Consider composite indexes for ORDER BY columns")
            
            if 'GROUP BY' in query_upper:
                optimizations["suggestions"].append("Indexes on GROUP BY columns can improve performance")
            
            # General performance tips
            if 'SELECT *' in query_upper:
                optimizations["performance_tips"].append("Avoid SELECT * - specify only needed columns")
            
            if 'LIKE' in query_upper and '%' in sql_query:
                optimizations["performance_tips"].append("Leading wildcards in LIKE queries prevent index usage")
            
            return {
                "status": "success",
                "optimizations": optimizations
            }
            
        except Exception as e:
            logger.error(f"Error optimizing query: {e}")
            return {
                "status": "error",
                "message": f"Optimization analysis failed: {str(e)}"
            }
    
    def _format_schema_for_llm(self, schema_context: Dict[str, Any], intent_data: Dict[str, Any]) -> str:
        """
        Format schema context for LLM consumption
        
        Args:
            schema_context: Raw schema context from database
            intent_data: Intent information to focus on relevant tables
            
        Returns:
            Formatted schema string for LLM
        """
        try:
            tables = schema_context.get('tables', {})
            relationships = schema_context.get('relationships', [])
            
            # Focus on relevant tables based on intent
            mentioned_table = intent_data.get('table_mentioned')
            relevant_tables = []
            
            if mentioned_table and mentioned_table in tables:
                relevant_tables.append(mentioned_table)
                
                # Add related tables through foreign keys
                for rel in relationships:
                    if rel.get('source_table') == mentioned_table:
                        relevant_tables.append(rel.get('target_table'))
                    elif rel.get('target_table') == mentioned_table:
                        relevant_tables.append(rel.get('source_table'))
            else:
                # If no specific table mentioned, include all tables
                relevant_tables = list(tables.keys())
            
            # Remove duplicates and limit to reasonable number
            relevant_tables = list(set(relevant_tables))[:10]  # Limit to 10 tables max
            
            # Format schema
            schema_lines = ["Database Schema:"]
            
            for table_name in relevant_tables:
                if table_name in tables:
                    table_info = tables[table_name]
                    columns = table_info.get('columns', {})
                    primary_keys = table_info.get('primary_keys', [])
                    foreign_keys = table_info.get('foreign_keys', [])
                    
                    schema_lines.append(f"\nTable: {table_name}")
                    
                    # Add columns
                    for col_name, col_info in columns.items():
                        data_type = col_info.get('data_type', 'unknown')
                        is_nullable = "" if col_info.get('is_nullable', True) else " NOT NULL"
                        pk_marker = " (PK)" if col_name in primary_keys else ""
                        
                        schema_lines.append(f"  - {col_name}: {data_type}{is_nullable}{pk_marker}")
                    
                    # Add foreign keys
                    if foreign_keys:
                        schema_lines.append("  Foreign Keys:")
                        for fk in foreign_keys:
                            schema_lines.append(f"    - {fk['source_column']} -> {fk['target_table']}.{fk['target_column']}")
            
            # Add relationships summary
            if relationships:
                schema_lines.append("\nTable Relationships:")
                for rel in relationships[:5]:  # Limit to 5 relationships
                    schema_lines.append(f"  - {rel['source_table']}.{rel['source_column']} -> {rel['target_table']}.{rel['target_column']}")
            
            return "\n".join(schema_lines)
            
        except Exception as e:
            logger.error(f"Error formatting schema for LLM: {e}")
            return f"Error formatting schema: {str(e)}"
    
    async def _generate_alternative_queries(self, intent_data: Dict[str, Any], formatted_schema: str) -> List[Dict[str, Any]]:
        """
        Generate alternative SQL queries for the same intent
        
        Args:
            intent_data: Intent information
            formatted_schema: Formatted schema context
            
        Returns:
            List of alternative query options
        """
        try:
            logger.info("Generating alternative queries")
            
            alternatives = []
            
            # Generate a simpler version
            simple_prompt = f"""
            Generate a simple, basic SQL query for this intent (avoid JOINs if possible):
            Intent: {intent_data}
            Schema: {formatted_schema}
            
            Return only the SQL query:
            """
            
            simple_query = await self.gemini_client.generate_content(simple_prompt)
            alternatives.append({
                "type": "simple",
                "query": simple_query.strip(),
                "description": "Simplified version without complex operations"
            })
            
            # Generate a more detailed version if original intent suggests complexity
            if intent_data.get('confidence', 0) > 0.7:
                detailed_prompt = f"""
                Generate a comprehensive SQL query with appropriate JOINs and conditions:
                Intent: {intent_data}
                Schema: {formatted_schema}
                
                Return only the SQL query:
                """
                
                detailed_query = await self.gemini_client.generate_content(detailed_prompt)
                alternatives.append({
                    "type": "detailed",
                    "query": detailed_query.strip(),
                    "description": "Comprehensive version with JOINs and detailed conditions"
                })
            
            return alternatives[:3]  # Limit to 3 alternatives
            
        except Exception as e:
            logger.error(f"Error generating alternative queries: {e}")
            return []

# Global instance
query_builder = None

def get_query_builder() -> QueryBuilderAgent:
    """Get or create global QueryBuilderAgent instance"""
    global query_builder
    if query_builder is None:
        query_builder = QueryBuilderAgent()
    return query_builder 