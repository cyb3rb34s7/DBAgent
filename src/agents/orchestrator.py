"""
PostgreSQL AI Agent MVP - Orchestrator Agent
Entry point and workflow coordinator for the AI agent system
"""

from typing import Dict, Any, Optional
import logging
import json

# Import workflows
from workflows.select_query_flow import select_query_workflow

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    """
    Orchestrator Agent - Entry point and workflow coordinator
    
    Responsibilities:
    - User input processing and intent extraction
    - Agent coordination and task delegation
    - Workflow planning based on query type
    - Response aggregation and user communication
    - Error handling and recovery coordination
    - Session context management
    """
    
    def __init__(self):
        """Initialize the Orchestrator Agent"""
        self.session_context = {}
        logger.info("OrchestratorAgent initialized")
    
    async def process_query(self, user_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point for processing user queries
        
        Args:
            user_query: Natural language query from user
            session_id: Optional session identifier for context
            
        Returns:
            Dict containing the response and metadata
        """
        try:
            logger.info(f"Processing query: {user_query}")
            
            # Step 1: Extract intent from user query
            intent = await self.extract_intent(user_query)
            logger.info(f"Extracted intent: {intent}")
            
            # Step 2: Route based on intent type
            if intent["type"] == "SELECT":
                response = await self._handle_select_query(user_query, intent)
            elif intent["type"] in ["UPDATE", "DELETE", "INSERT"]:
                response = await self._handle_destructive_query(user_query, intent)
            else:
                response = {
                    "status": "error",
                    "message": f"Unsupported query type: {intent['type']}",
                    "query": user_query
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "status": "error",
                "message": f"Failed to process query: {str(e)}",
                "query": user_query
            }
    
    async def extract_intent(self, user_query: str) -> Dict[str, Any]:
        """
        Extract intent from user query using basic rules
        
        Args:
            user_query: Natural language query
            
        Returns:
            Dict containing intent information
        """
        query_lower = user_query.lower().strip()
        
        # Basic intent classification using static rules
        if any(keyword in query_lower for keyword in ["show me", "select", "get", "find", "list", "display"]):
            intent_type = "SELECT"
            confidence = 0.8
        elif any(keyword in query_lower for keyword in ["update", "modify", "change", "set"]):
            intent_type = "UPDATE"
            confidence = 0.8
        elif any(keyword in query_lower for keyword in ["delete", "remove", "drop"]):
            intent_type = "DELETE"
            confidence = 0.8
        elif any(keyword in query_lower for keyword in ["insert", "add", "create", "new"]):
            intent_type = "INSERT"
            confidence = 0.8
        else:
            intent_type = "UNKNOWN"
            confidence = 0.1
        
        intent = {
            "type": intent_type,
            "confidence": confidence,
            "original_query": user_query,
            "keywords": self._extract_keywords(query_lower)
        }
        
        return intent
    
    def _extract_keywords(self, query: str) -> list:
        """Extract potential table/column keywords from query"""
        # Simple keyword extraction - will be enhanced later
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "where", "all", "me", "my"}
        words = query.split()
        keywords = [word for word in words if word not in common_words and len(word) > 2]
        return keywords
    
    async def _handle_select_query(self, user_query: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SELECT queries using LangGraph workflow"""
        logger.info("Handling SELECT query with LangGraph workflow")
        
        try:
            # Run the SELECT query workflow
            workflow_result = await select_query_workflow.run(user_query, intent)
            
            # Format the response for the client
            if workflow_result.get("status") == "success":
                results = workflow_result.get("results", {})
                
                return {
                    "status": results.get("status", "success"),
                    "type": "SELECT",
                    "message": results.get("message", "Query executed successfully"),
                    "query": user_query,
                    "sql_query": workflow_result.get("sql_query", ""),
                    "data": results.get("data", []),
                    "metadata": results.get("metadata", {}),
                    "intent": intent,
                    "workflow": "langgraph_select"
                }
            else:
                return {
                    "status": "error",
                    "type": "SELECT",
                    "message": workflow_result.get("message", "Workflow execution failed"),
                    "query": user_query,
                    "intent": intent,
                    "workflow": "langgraph_select"
                }
                
        except Exception as e:
            logger.error(f"Error in SELECT query workflow: {e}")
            return {
                "status": "error",
                "type": "SELECT",
                "message": f"Workflow error: {str(e)}",
                "query": user_query,
                "intent": intent
            }
    
    async def _handle_destructive_query(self, user_query: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle UPDATE/DELETE/INSERT queries (require approval)"""
        logger.info(f"Handling destructive query: {intent['type']}")
        
        # For now, return a placeholder response
        # This will be enhanced when we implement the Impact Analysis Agent
        return {
            "status": "pending_approval",
            "type": intent["type"],
            "message": f"{intent['type']} query requires approval (not yet implemented)",
            "query": user_query,
            "intent": intent
        }
    
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get session context for a given session ID"""
        return self.session_context.get(session_id, {})
    
    def update_session_context(self, session_id: str, context: Dict[str, Any]):
        """Update session context for a given session ID"""
        if session_id not in self.session_context:
            self.session_context[session_id] = {}
        self.session_context[session_id].update(context) 