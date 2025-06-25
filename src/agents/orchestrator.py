"""
PostgreSQL AI Agent MVP - Orchestrator Agent
Enhanced orchestrator with Gemini AI integration and unified workflow routing
"""

import logging
from typing import Dict, Any, Optional
from utils.gemini_client import get_gemini_client

# Import workflows - Updated for P3.T4.2
from workflows.unified_query_flow import unified_query_workflow

logger = logging.getLogger(__name__)

class OrchestratorAgent:
    """
    Enhanced orchestrator agent that processes user queries and routes them to appropriate workflows
    Uses Gemini AI for intent extraction with fallback to basic rules
    """
    
    def __init__(self):
        """Initialize the orchestrator agent"""
        self.gemini_client = get_gemini_client()
        self.session_contexts = {}
        logger.info("Enhanced OrchestratorAgent initialized with Gemini AI integration")
    
    async def process_query(self, user_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a user query and route it to the appropriate workflow
        
        Args:
            user_query: Natural language query from user
            session_id: Optional session identifier for context
            
        Returns:
            Dict containing query results and metadata
        """
        logger.info(f"Processing query: {user_query[:100]}...")
        
        try:
            # Step 1: Extract intent using Gemini AI
            intent = await self.extract_intent(user_query)
            logger.info(f"Intent extracted: {intent['type']} (confidence: {intent['confidence']})")
            
            # Step 2: P3.T4.2 - Use unified workflow for all queries
            # This allows conditional routing AFTER query building
            logger.info("Routing to unified workflow for conditional routing after query building")
            result = await unified_query_workflow.run(user_query, intent)
            
            # Add orchestrator metadata
            result["orchestrator_intent"] = intent
            result["gemini_used"] = not intent.get("fallback_used", False)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "status": "error",
                "message": f"Query processing failed: {str(e)}",
                "query": user_query,
                "workflow": "orchestrator_error"
            }

    async def extract_intent(self, user_query: str) -> Dict[str, Any]:
        """
        Extract intent from user query using Gemini AI with fallback
        
        Args:
            user_query: Natural language query
            
        Returns:
            Dict containing intent information
        """
        try:
            # Try Gemini AI first
            prompt = f"""
            Analyze this database query and extract the intent. Return a JSON object with:
            - type: The SQL operation type (SELECT, UPDATE, DELETE, INSERT, or UNKNOWN)
            - confidence: Float between 0.0 and 1.0 indicating confidence in classification
            - keywords: Array of important keywords from the query
            - table_mentioned: The main table name mentioned (if any)
            - operation_type: Either "READ" for SELECT or "WRITE" for modifications
            
            Query: "{user_query}"
            
            Return only the JSON object, no other text.
            """
            
            response = await self.gemini_client.generate_content(prompt)
            
            if response:
                # Parse the JSON response
                import json
                intent_text = response.strip()
                
                # Remove any markdown formatting
                if intent_text.startswith("```json"):
                    intent_text = intent_text.replace("```json", "").replace("```", "").strip()
                elif intent_text.startswith("```"):
                    intent_text = intent_text.replace("```", "").strip()
                
                intent = json.loads(intent_text)
                
                # Validate and enhance the intent
                intent["original_query"] = user_query
                intent["fallback_used"] = False
                
                logger.info(f"Gemini intent extraction successful: {intent['type']}")
                return intent
            else:
                logger.warning("Gemini API returned empty response")
                raise Exception("Gemini API empty response")
            
        except Exception as e:
            logger.error(f"Error extracting intent with Gemini: {e}")
            
            # Fallback to basic rules if Gemini fails
            logger.info("Falling back to basic intent extraction")
            return await self._extract_intent_fallback(user_query)
    
    async def _extract_intent_fallback(self, user_query: str) -> Dict[str, Any]:
        """
        Fallback intent extraction using basic rules
        
        Args:
            user_query: Natural language query
            
        Returns:
            Dict containing intent information
        """
        query_lower = user_query.lower().strip()
        
        # Basic intent classification using static rules
        if any(keyword in query_lower for keyword in ["show me", "select", "get", "find", "list", "display"]):
            intent_type = "SELECT"
            confidence = 0.6  # Lower confidence for fallback
        elif any(keyword in query_lower for keyword in ["update", "modify", "change", "set"]):
            intent_type = "UPDATE"
            confidence = 0.6
        elif any(keyword in query_lower for keyword in ["delete", "remove", "drop"]):
            intent_type = "DELETE"
            confidence = 0.6
        elif any(keyword in query_lower for keyword in ["insert", "add", "create", "new"]):
            intent_type = "INSERT"
            confidence = 0.6
        else:
            intent_type = "UNKNOWN"
            confidence = 0.1
        
        intent = {
            "type": intent_type,
            "confidence": confidence,
            "original_query": user_query,
            "keywords": self._extract_keywords(query_lower),
            "table_mentioned": None,
            "operation_type": "READ" if intent_type == "SELECT" else "WRITE" if intent_type in ["UPDATE", "DELETE", "INSERT"] else "UNKNOWN",
            "fallback_used": True
        }
        
        return intent
    
    def _extract_keywords(self, query: str) -> list:
        """Extract potential table/column keywords from query"""
        # Simple keyword extraction
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "where", "all", "me", "my"}
        words = query.split()
        keywords = [word for word in words if word not in common_words and len(word) > 2]
        return keywords

    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get session context for a given session ID"""
        return self.session_contexts.get(session_id, {})
    
    def update_session_context(self, session_id: str, context: Dict[str, Any]):
        """Update session context for a given session ID"""
        if session_id not in self.session_contexts:
            self.session_contexts[session_id] = {}
        self.session_contexts[session_id].update(context) 