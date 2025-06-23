"""
PostgreSQL AI Agent MVP - SELECT Query LangGraph Workflow
Enhanced workflow for processing SELECT queries with schema context and AI generation
"""

from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END, START
import logging

# Import our tools
from tools.db_ops import execute_select_query, fetch_schema_context, build_sql_query, validate_query

logger = logging.getLogger(__name__)

class SelectQueryState(TypedDict):
    """Enhanced state for the SELECT query workflow"""
    user_query: str
    intent: Dict[str, Any]
    schema_context: Dict[str, Any]
    sql_query: str
    validation_result: Dict[str, Any]
    results: Dict[str, Any]
    error: str
    metadata: Dict[str, Any]

class SelectQueryWorkflow:
    """Enhanced LangGraph workflow for processing SELECT queries"""
    
    def __init__(self):
        """Initialize the enhanced SELECT query workflow"""
        self.graph = self._build_graph()
        logger.info("Enhanced SelectQueryWorkflow initialized")
    
    def _build_graph(self) -> StateGraph:
        """Build the enhanced LangGraph workflow"""
        
        # Define the workflow graph
        workflow = StateGraph(SelectQueryState)
        
        # Add nodes for the enhanced pipeline
        workflow.add_node("fetch_schema", self._fetch_schema_node)
        workflow.add_node("build_query", self._build_query_node)
        workflow.add_node("validate_query", self._validate_query_node)
        workflow.add_node("execute_query", self._execute_query_node)
        
        # Define the enhanced flow
        # START -> fetch_schema -> build_query -> validate_query -> execute_query -> END
        workflow.add_edge(START, "fetch_schema")
        workflow.add_edge("fetch_schema", "build_query")
        workflow.add_edge("build_query", "validate_query")
        workflow.add_edge("validate_query", "execute_query")
        workflow.add_edge("execute_query", END)
        
        # Compile the graph
        return workflow.compile()
    
    async def _fetch_schema_node(self, state: SelectQueryState) -> SelectQueryState:
        """
        Fetch database schema context node
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with schema context
        """
        try:
            logger.info("Fetching schema context")
            
            intent = state.get("intent", {})
            table_mentioned = intent.get("table_mentioned")
            
            # Fetch schema context (with caching)
            if table_mentioned:
                schema_result = await fetch_schema_context(table_names=[table_mentioned])
            else:
                schema_result = await fetch_schema_context()
            
            if schema_result.get("status") == "success":
                logger.info(f"Schema context fetched successfully (cached: {schema_result.get('cached', False)})")
                return {
                    **state,
                    "schema_context": schema_result.get("schema_context", {}),
                    "metadata": {
                        **state.get("metadata", {}),
                        "schema_cached": schema_result.get("cached", False),
                        "schema_tables_count": len(schema_result.get("schema_context", {}).get("tables", {}))
                    }
                }
            else:
                logger.error(f"Schema fetch failed: {schema_result.get('message')}")
                return {
                    **state,
                    "error": f"Schema fetch failed: {schema_result.get('message')}",
                    "schema_context": {}
                }
                
        except Exception as e:
            logger.error(f"Error in fetch_schema_node: {e}")
            return {
                **state,
                "error": f"Schema fetch error: {str(e)}",
                "schema_context": {}
            }
    
    async def _build_query_node(self, state: SelectQueryState) -> SelectQueryState:
        """
        Build SQL query using AI and schema context
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with generated SQL query
        """
        try:
            logger.info("Building SQL query using AI")
            
            intent = state.get("intent", {})
            schema_context = state.get("schema_context", {})
            
            # Check if we have an error from previous step
            if state.get("error"):
                logger.warning("Skipping query building due to previous error")
                return state
            
            # Build SQL query using intent and schema context
            query_result = await build_sql_query(intent)
            
            if query_result.get("status") == "success":
                sql_query = query_result.get("sql_query", "")
                logger.info(f"SQL query built successfully: {sql_query[:100]}...")
                
                return {
                    **state,
                    "sql_query": sql_query,
                    "metadata": {
                        **state.get("metadata", {}),
                        "query_generated": True,
                        "alternatives_count": len(query_result.get("alternatives", [])),
                        "schema_used_tables": query_result.get("schema_used", {}).get("tables_count", 0)
                    }
                }
            else:
                logger.error(f"Query building failed: {query_result.get('message')}")
                return {
                    **state,
                    "error": f"Query building failed: {query_result.get('message')}",
                    "sql_query": ""
                }
                
        except Exception as e:
            logger.error(f"Error in build_query_node: {e}")
            return {
                **state,
                "error": f"Query building error: {str(e)}",
                "sql_query": ""
            }
    
    async def _validate_query_node(self, state: SelectQueryState) -> SelectQueryState:
        """
        Validate the generated SQL query
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with validation results
        """
        try:
            logger.info("Validating generated SQL query")
            
            sql_query = state.get("sql_query", "")
            
            # Check if we have an error from previous step
            if state.get("error") or not sql_query:
                logger.warning("Skipping query validation due to previous error or empty query")
                return {
                    **state,
                    "validation_result": {"is_valid": False, "issues": ["No query to validate"]}
                }
            
            # Validate the SQL query
            validation_result = await validate_query(sql_query)
            
            logger.info(f"Query validation completed: {validation_result.get('is_valid')}")
            
            return {
                **state,
                "validation_result": validation_result,
                "metadata": {
                    **state.get("metadata", {}),
                    "query_valid": validation_result.get("is_valid", False),
                    "query_complexity": validation_result.get("complexity", "UNKNOWN")
                }
            }
            
        except Exception as e:
            logger.error(f"Error in validate_query_node: {e}")
            return {
                **state,
                "error": f"Query validation error: {str(e)}",
                "validation_result": {"is_valid": False, "issues": [f"Validation error: {str(e)}"]}
            }
    
    async def _execute_query_node(self, state: SelectQueryState) -> SelectQueryState:
        """
        Execute the validated SQL query
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with query results
        """
        try:
            logger.info("Executing validated SQL query")
            
            sql_query = state.get("sql_query", "")
            validation_result = state.get("validation_result", {})
            
            # Check if we have an error from previous steps
            if state.get("error"):
                logger.warning("Skipping query execution due to previous error")
                return {
                    **state,
                    "results": {
                        "status": "error",
                        "message": state.get("error"),
                        "data": []
                    }
                }
            
            # Check if query is valid
            if not validation_result.get("is_valid", False):
                issues = validation_result.get("issues", ["Query validation failed"])
                logger.warning(f"Skipping execution of invalid query: {issues}")
                return {
                    **state,
                    "results": {
                        "status": "error",
                        "message": f"Query validation failed: {', '.join(issues)}",
                        "data": [],
                        "validation_issues": issues
                    }
                }
            
            # Execute the query using our database tool
            results = await execute_select_query(sql_query)
            
            logger.info(f"Query execution completed with status: {results.get('status')}")
            
            return {
                **state,
                "results": results,
                "metadata": {
                    **state.get("metadata", {}),
                    "execution_successful": results.get("status") == "success",
                    "rows_returned": len(results.get("data", [])) if results.get("status") == "success" else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in execute_query_node: {e}")
            return {
                **state,
                "error": str(e),
                "results": {
                    "status": "error",
                    "message": f"Execution error: {str(e)}",
                    "data": []
                }
            }
    
    async def run(self, user_query: str, intent: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run the enhanced SELECT query workflow
        
        Args:
            user_query: User's query
            intent: Extracted intent (required for enhanced workflow)
            
        Returns:
            Workflow results
        """
        try:
            logger.info(f"Running enhanced SELECT query workflow for: {user_query}")
            
            # Initialize enhanced state
            initial_state = SelectQueryState(
                user_query=user_query,
                intent=intent or {},
                schema_context={},
                sql_query="",
                validation_result={},
                results={},
                error="",
                metadata={}
            )
            
            # Run the enhanced workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            # Return comprehensive results
            return {
                "status": "success" if not final_state.get("error") else "error",
                "workflow": "enhanced_select_query",
                "user_query": user_query,
                "intent": final_state.get("intent", {}),
                "sql_query": final_state.get("sql_query", ""),
                "validation": final_state.get("validation_result", {}),
                "results": final_state.get("results", {}),
                "metadata": final_state.get("metadata", {}),
                "error": final_state.get("error", "")
            }
            
        except Exception as e:
            logger.error(f"Error running enhanced SELECT query workflow: {e}")
            return {
                "status": "error",
                "workflow": "enhanced_select_query",
                "message": f"Workflow execution failed: {str(e)}",
                "user_query": user_query,
                "error": str(e)
            }

# Global enhanced workflow instance
select_query_workflow = SelectQueryWorkflow() 