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
        Format enhanced schema context for intelligent LLM consumption
        
        Args:
            schema_context: Enhanced schema context from database with entity mappings
            intent_data: Intent information to focus on relevant tables
            
        Returns:
            Intelligently formatted schema string for LLM with entity mappings
        """
        try:
            # Extract enhanced schema components
            tables = schema_context.get('tables', {})
            entity_mappings = schema_context.get('entity_mappings', {})
            natural_language_guide = schema_context.get('natural_language_guide', {})
            column_value_analysis = schema_context.get('column_value_analysis', {})
            semantic_context = schema_context.get('semantic_context', {})
            
            schema_lines = ["=== INTELLIGENT DATABASE SCHEMA GUIDE ==="]
            
            # 1. Available Tables (Critical - AI must use ONLY these)
            schema_lines.append("\n🏗️ AVAILABLE TABLES (USE ONLY THESE):")
            available_tables = natural_language_guide.get('available_tables', list(tables.keys()))
            for table_name in available_tables:
                estimated_rows = tables.get(table_name, {}).get('estimated_rows', 0)
                purpose = semantic_context.get('table_purposes', {}).get(table_name, f"Stores {table_name} data")
                schema_lines.append(f"  ✓ {table_name} ({estimated_rows} rows) - {purpose}")
            
            # 2. Entity Resolution Guide (Critical for "clients" -> users WHERE role='client')
            entity_resolution = natural_language_guide.get('entity_resolution', {})
            if entity_resolution:
                schema_lines.append("\n🔍 ENTITY RESOLUTION GUIDE (CRITICAL):")
                schema_lines.append("When user mentions these entities, use the corresponding SQL:")
                for entity, mapping in entity_resolution.items():
                    maps_to = mapping.get('maps_to', '')
                    description = mapping.get('description', '')
                    schema_lines.append(f"  • '{entity}' → {maps_to}")
                    if description:
                        schema_lines.append(f"    ({description})")
            
            # 3. Detailed Table Structures
            schema_lines.append("\n📋 TABLE STRUCTURES:")
            for table_name in available_tables:
                if table_name in tables:
                    table_info = tables[table_name]
                    columns = table_info.get('columns', {})
                    primary_keys = table_info.get('primary_keys', [])
                    
                    schema_lines.append(f"\n  📊 Table: {table_name}")
                    
                    # Add columns with enhanced information
                    for col_name, col_info in columns.items():
                        data_type = col_info.get('data_type', 'unknown')
                        is_nullable = "" if col_info.get('is_nullable', True) else " NOT NULL"
                        pk_marker = " (PRIMARY KEY)" if col_name in primary_keys else ""
                        
                        # Get column value analysis
                        col_analysis = column_value_analysis.get(table_name, {}).get(col_name, {})
                        semantic_type = col_analysis.get('semantic_type', 'unknown')
                        
                        column_line = f"    - {col_name}: {data_type}{is_nullable}{pk_marker}"
                        
                        # Add categorical values if available
                        if col_analysis.get('is_categorical') and col_analysis.get('unique_values'):
                            values = col_analysis['unique_values']
                            column_line += f" [VALUES: {', '.join(map(str, values))}]"
                        elif col_analysis.get('sample_values'):
                            samples = col_analysis['sample_values'][:3]
                            column_line += f" [SAMPLES: {', '.join(map(str, samples))}]"
                        
                        if semantic_type != 'unknown':
                            column_line += f" ({semantic_type})"
                        
                        schema_lines.append(column_line)
            
            # 4. Query Examples
            query_examples = natural_language_guide.get('query_examples', {})
            if query_examples:
                schema_lines.append("\n💡 QUERY EXAMPLES:")
                for table_name, examples in query_examples.items():
                    if examples:
                        schema_lines.append(f"  For {table_name}:")
                        for example in examples[:3]:  # Limit to 3 examples per table
                            schema_lines.append(f"    • \"{example}\"")
            
            # 5. Important Rules
            important_notes = natural_language_guide.get('important_notes', [])
            if important_notes:
                schema_lines.append("\n⚠️ CRITICAL RULES:")
                for i, note in enumerate(important_notes, 1):
                    schema_lines.append(f"  {i}. {note}")
            
            # 6. Relationships (if any)
            relationships = schema_context.get('relationships', [])
            if relationships:
                schema_lines.append("\n🔗 TABLE RELATIONSHIPS:")
                for rel in relationships[:5]:  # Limit to 5 relationships
                    schema_lines.append(f"  • {rel['source_table']}.{rel['source_column']} → {rel['target_table']}.{rel['target_column']}")
            
            # 7. Final Reminder
            schema_lines.append("\n🎯 REMEMBER:")
            schema_lines.append("  • NEVER create queries for non-existent tables")
            schema_lines.append("  • ALWAYS use entity resolution guide for concept mapping")
            schema_lines.append("  • USE ONLY the available tables listed above")
            schema_lines.append("  • Check categorical values for exact column values")
            
            return "\n".join(schema_lines)
            
        except Exception as e:
            logger.error(f"Error formatting enhanced schema for LLM: {e}")
            return f"Error formatting enhanced schema: {str(e)}"
    
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