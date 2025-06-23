"""
PostgreSQL AI Agent MVP - SELECT Query LangGraph Workflow
Simple workflow for processing SELECT queries
"""

from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END, START
import logging

# Import our tools
from tools.db_ops import execute_select_query

logger = logging.getLogger(__name__)

class SelectQueryState(TypedDict):
    """State for the SELECT query workflow"""
    user_query: str
    intent: Dict[str, Any]
    sql_query: str
    results: Dict[str, Any]
    error: str

class SelectQueryWorkflow:
    """LangGraph workflow for processing SELECT queries"""
    
    def __init__(self):
        """Initialize the SELECT query workflow"""
        self.graph = self._build_graph()
        logger.info("SelectQueryWorkflow initialized")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Define the workflow graph
        workflow = StateGraph(SelectQueryState)
        
        # Add nodes
        workflow.add_node("execute_query", self._execute_query_node)
        
        # Define the flow
        workflow.add_edge(START, "execute_query")
        workflow.add_edge("execute_query", END)
        
        # Compile the graph
        return workflow.compile()
    
    async def _execute_query_node(self, state: SelectQueryState) -> SelectQueryState:
        """
        Execute the SQL query node
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with query results
        """
        try:
            logger.info(f"Executing query node for: {state.get('user_query', 'Unknown')}")
            
            # For now, we'll use a simple approach - the user query is treated as SQL
            # In Phase 2, this will be enhanced with proper SQL generation
            user_query = state.get("user_query", "")
            
            # Simple heuristic: if it looks like SQL, use it directly
            # Otherwise, create a basic SELECT statement
            if user_query.strip().upper().startswith("SELECT"):
                sql_query = user_query
            else:
                # For MVP, we'll return a helpful message for non-SQL queries
                return {
                    **state,
                    "results": {
                        "status": "info",
                        "message": "For MVP, please provide a valid SELECT SQL query. Natural language processing will be added in Phase 2.",
                        "example": "Try: SELECT version() or SELECT current_timestamp"
                    },
                    "sql_query": ""
                }
            
            # Execute the query using our database tool
            results = await execute_select_query(sql_query)
            
            logger.info(f"Query execution completed with status: {results.get('status')}")
            
            return {
                **state,
                "sql_query": sql_query,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in execute_query_node: {e}")
            return {
                **state,
                "error": str(e),
                "results": {
                    "status": "error",
                    "message": f"Workflow error: {str(e)}"
                }
            }
    
    async def run(self, user_query: str, intent: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run the SELECT query workflow
        
        Args:
            user_query: User's query
            intent: Extracted intent (optional)
            
        Returns:
            Workflow results
        """
        try:
            logger.info(f"Running SELECT query workflow for: {user_query}")
            
            # Initialize state
            initial_state = SelectQueryState(
                user_query=user_query,
                intent=intent or {},
                sql_query="",
                results={},
                error=""
            )
            
            # Run the workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            # Return the results
            return {
                "status": "success",
                "workflow": "select_query",
                "user_query": user_query,
                "sql_query": final_state.get("sql_query", ""),
                "results": final_state.get("results", {}),
                "error": final_state.get("error", "")
            }
            
        except Exception as e:
            logger.error(f"Error running SELECT query workflow: {e}")
            return {
                "status": "error",
                "workflow": "select_query",
                "message": f"Workflow execution failed: {str(e)}",
                "user_query": user_query
            }

# Global workflow instance
select_query_workflow = SelectQueryWorkflow() 