"""
PostgreSQL AI Agent MVP - Destructive Query Workflow
LangGraph workflow for handling UPDATE, DELETE, INSERT operations with safety controls
"""

import logging
from typing import Dict, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

# Import agents and tools
from agents.query_builder import QueryBuilderAgent
from agents.impact_analysis import ImpactAnalysisAgent
from tools.db_ops import fetch_schema_context
from tools.impact_execution import analyze_query_impact, create_approval_request, check_approval_status, execute_approved_query, update_approval_status

logger = logging.getLogger(__name__)

class DestructiveQueryState(TypedDict):
    """State for destructive query processing workflow"""
    # Input
    user_query: str
    intent: Dict[str, Any]
    
    # Schema context
    schema_context: Dict[str, Any]
    
    # Query building
    sql_query: str
    validation_result: Dict[str, Any]
    
    # Impact analysis
    impact_analysis: Dict[str, Any]
    risk_level: str
    
    # Approval workflow
    approval_ticket: Dict[str, Any]
    approval_status: str
    approval_required: bool
    
    # Execution
    execution_result: Dict[str, Any]
    
    # Metadata
    workflow_status: str
    error_message: str
    metadata: Dict[str, Any]

class DestructiveQueryWorkflow:
    """LangGraph workflow for destructive query processing"""
    
    def __init__(self):
        """Initialize the destructive query workflow"""
        self.query_builder = QueryBuilderAgent()
        self.impact_analyzer = ImpactAnalysisAgent()
        
        # Build the workflow graph
        self.graph = self._build_graph()
        logger.info("DestructiveQueryWorkflow initialized")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow graph"""
        workflow = StateGraph(DestructiveQueryState)
        
        # Add nodes
        workflow.add_node("fetch_schema", self._fetch_schema_node)
        workflow.add_node("build_query", self._build_query_node)
        workflow.add_node("validate_query", self._validate_query_node)
        workflow.add_node("analyze_impact", self._analyze_impact_node)
        workflow.add_node("check_approval_required", self._check_approval_required_node)
        workflow.add_node("create_approval", self._create_approval_node)
        workflow.add_node("wait_approval", self._wait_approval_node)
        workflow.add_node("execute_query", self._execute_query_node)
        
        # Define the workflow
        workflow.add_edge(START, "fetch_schema")
        workflow.add_edge("fetch_schema", "build_query")
        workflow.add_edge("build_query", "validate_query")
        workflow.add_edge("validate_query", "analyze_impact")
        workflow.add_edge("analyze_impact", "check_approval_required")
        
        # Conditional routing based on approval requirement
        workflow.add_conditional_edges(
            "check_approval_required",
            self._approval_router,
            {
                "auto_approve": "execute_query",
                "require_approval": "create_approval",
                "error": END
            }
        )
        
        workflow.add_edge("create_approval", "wait_approval")
        
        # Conditional routing based on approval status
        workflow.add_conditional_edges(
            "wait_approval",
            self._approval_status_router,
            {
                "approved": "execute_query",
                "rejected": END,
                "pending": "wait_approval",
                "expired": END,
                "error": END
            }
        )
        
        workflow.add_edge("execute_query", END)
        
        return workflow.compile()
    
    async def _fetch_schema_node(self, state: DestructiveQueryState) -> DestructiveQueryState:
        """Fetch database schema context"""
        logger.info("Fetching schema context for destructive query")
        
        try:
            # Extract table names from intent if available
            table_names = []
            if state["intent"].get("table_mentioned"):
                table_names.append(state["intent"]["table_mentioned"])
            
            # Fetch schema context
            schema_result = await fetch_schema_context(table_names=table_names)
            
            if schema_result.get("status") == "success":
                state["schema_context"] = schema_result.get("schema_context", {})
                state["metadata"]["schema_cached"] = schema_result.get("cached", False)
                logger.info("Schema context fetched successfully")
            else:
                state["workflow_status"] = "error"
                state["error_message"] = f"Failed to fetch schema: {schema_result.get('message')}"
                logger.error(f"Schema fetch failed: {state['error_message']}")
            
        except Exception as e:
            state["workflow_status"] = "error"
            state["error_message"] = f"Schema fetch error: {str(e)}"
            logger.error(f"Error in fetch_schema_node: {e}")
        
        return state
    
    async def _build_query_node(self, state: DestructiveQueryState) -> DestructiveQueryState:
        """Build SQL query from natural language"""
        logger.info("Building SQL query for destructive operation")
        
        try:
            if state.get("workflow_status") == "error":
                return state
            
            # Build SQL query using QueryBuilderAgent
            query_result = await self.query_builder.build_sql_query(
                intent_data=state["intent"],
                table_names=[state["intent"].get("table_mentioned")] if state["intent"].get("table_mentioned") else None
            )
            
            if query_result.get("status") == "success":
                state["sql_query"] = query_result.get("sql_query", "")
                state["metadata"]["query_builder_used"] = True
                logger.info(f"SQL query built successfully: {state['sql_query'][:100]}...")
            else:
                state["workflow_status"] = "error"
                state["error_message"] = f"Query building failed: {query_result.get('message')}"
                logger.error(f"Query building failed: {state['error_message']}")
            
        except Exception as e:
            state["workflow_status"] = "error"
            state["error_message"] = f"Query building error: {str(e)}"
            logger.error(f"Error in build_query_node: {e}")
        
        return state
    
    async def _validate_query_node(self, state: DestructiveQueryState) -> DestructiveQueryState:
        """Validate the generated SQL query"""
        logger.info("Validating destructive SQL query")
        
        try:
            if state.get("workflow_status") == "error":
                return state
            
            # Check if we have a valid SQL query to validate
            sql_query = state.get("sql_query", "")
            if not sql_query or sql_query.strip() == "":
                state["workflow_status"] = "error"
                state["error_message"] = "No SQL query generated to validate"
                logger.error("No SQL query available for validation")
                return state
            
            # Validate query using QueryBuilderAgent
            validation_result = await self.query_builder.validate_query(sql_query)
            
            # Ensure validation_result is not None
            if validation_result is None:
                state["workflow_status"] = "error"
                state["error_message"] = "Query validation returned None result"
                logger.error("Query validation returned None")
                return state
            
            state["validation_result"] = validation_result
            
            # Check if query is valid (validate_query returns is_valid directly, not status)
            if not validation_result.get("is_valid", False):
                issues = validation_result.get("issues", ["Unknown validation issue"])
                state["workflow_status"] = "error"
                state["error_message"] = f"Query validation failed: {'; '.join(issues)}"
                logger.error(f"Query validation failed: {state['error_message']}")
            else:
                logger.info("Query validation passed")
            
        except Exception as e:
            state["workflow_status"] = "error"
            state["error_message"] = f"Query validation error: {str(e)}"
            logger.error(f"Error in validate_query_node: {e}")
        
        return state
    
    async def _analyze_impact_node(self, state: DestructiveQueryState) -> DestructiveQueryState:
        """Analyze the impact of the destructive query"""
        logger.info("Analyzing query impact and risk")
        
        try:
            if state.get("workflow_status") == "error":
                return state
            
            # Analyze impact using ImpactAnalysisAgent
            impact_result = await self.impact_analyzer.analyze_query_impact(
                sql_query=state["sql_query"],
                intent_data=state["intent"]
            )
            
            state["impact_analysis"] = impact_result
            
            if impact_result.get("status") == "success":
                risk_classification = impact_result.get("risk_classification", {})
                state["risk_level"] = risk_classification.get("level", "UNKNOWN")
                logger.info(f"Impact analysis completed: {state['risk_level']} risk")
            else:
                state["workflow_status"] = "error"
                state["error_message"] = f"Impact analysis failed: {impact_result.get('message')}"
                logger.error(f"Impact analysis failed: {state['error_message']}")
            
        except Exception as e:
            state["workflow_status"] = "error"
            state["error_message"] = f"Impact analysis error: {str(e)}"
            logger.error(f"Error in analyze_impact_node: {e}")
        
        return state
    
    async def _check_approval_required_node(self, state: DestructiveQueryState) -> DestructiveQueryState:
        """Check if approval is required based on risk level"""
        logger.info(f"Checking approval requirement for {state.get('risk_level', 'UNKNOWN')} risk")
        
        try:
            if state.get("workflow_status") == "error":
                return state
            
            risk_level = state.get("risk_level", "UNKNOWN")
            
            # Approval required for HIGH and CRITICAL risk levels
            if risk_level in ["HIGH", "CRITICAL"]:
                state["approval_required"] = True
                logger.info(f"Approval required for {risk_level} risk level")
            elif risk_level in ["LOW", "MEDIUM"]:
                state["approval_required"] = False
                logger.info(f"Auto-approval for {risk_level} risk level")
            else:
                # Unknown risk level - require approval for safety
                state["approval_required"] = True
                logger.warning(f"Unknown risk level {risk_level}, requiring approval for safety")
            
        except Exception as e:
            state["workflow_status"] = "error"
            state["error_message"] = f"Approval check error: {str(e)}"
            logger.error(f"Error in check_approval_required_node: {e}")
        
        return state
    
    async def _create_approval_node(self, state: DestructiveQueryState) -> DestructiveQueryState:
        """Create approval request ticket"""
        logger.info("Creating approval request ticket")
        
        try:
            if state.get("workflow_status") == "error":
                return state
            
            # Create approval request with correct parameters
            approval_result = await create_approval_request(
                sql_query=state["sql_query"],
                impact_analysis=state["impact_analysis"],
                requester_info={
                    "user_query": state["user_query"],
                    "intent": state["intent"],
                    "workflow": "destructive_query_langgraph"
                }
            )
            
            state["approval_ticket"] = approval_result
            
            if approval_result.get("status") == "success":
                state["approval_status"] = "pending"
                logger.info(f"Approval ticket created: {approval_result.get('ticket_id')}")
            else:
                state["workflow_status"] = "error"
                state["error_message"] = f"Failed to create approval ticket: {approval_result.get('message')}"
                logger.error(f"Approval ticket creation failed: {state['error_message']}")
            
        except Exception as e:
            state["workflow_status"] = "error"
            state["error_message"] = f"Approval creation error: {str(e)}"
            logger.error(f"Error in create_approval_node: {e}")
        
        return state
    
    async def _wait_approval_node(self, state: DestructiveQueryState) -> DestructiveQueryState:
        """Wait for approval decision"""
        logger.info("Checking approval status")
        
        try:
            if state.get("workflow_status") == "error":
                return state
            
            ticket_id = state["approval_ticket"].get("ticket_id")
            if not ticket_id:
                state["workflow_status"] = "error"
                state["error_message"] = "No ticket ID available for approval check"
                return state
            
            # Check approval status
            status_result = await check_approval_status(ticket_id)
            
            if status_result.get("status") == "success":
                approval_data = status_result.get("approval_data", {})
                state["approval_status"] = approval_data.get("status", "unknown")
                logger.info(f"Approval status: {state['approval_status']}")
            else:
                state["workflow_status"] = "error"
                state["error_message"] = f"Failed to check approval status: {status_result.get('message')}"
                logger.error(f"Approval status check failed: {state['error_message']}")
            
        except Exception as e:
            state["workflow_status"] = "error"
            state["error_message"] = f"Approval status error: {str(e)}"
            logger.error(f"Error in wait_approval_node: {e}")
        
        return state
    
    async def _execute_query_node(self, state: DestructiveQueryState) -> DestructiveQueryState:
        """Execute the approved destructive query safely"""
        logger.info("Executing approved destructive query")
        
        try:
            if state.get("workflow_status") == "error":
                return state
            
            # Execute the query safely
            if state.get("approval_required", False):
                # Execute approved query using ticket
                ticket_id = state["approval_ticket"].get("ticket_id")
                if not ticket_id:
                    state["workflow_status"] = "error"
                    state["error_message"] = "No ticket ID available for approved query execution"
                    return state
                
                execution_result = await execute_approved_query(ticket_id)
            else:
                # Auto-approved query - create temporary approval and execute
                logger.info("Executing auto-approved query with temporary ticket")
                
                # Create temporary approval request for auto-approved query
                temp_approval_result = await create_approval_request(
                    sql_query=state["sql_query"],
                    impact_analysis=state["impact_analysis"],
                    requester_info={
                        "user_query": state["user_query"],
                        "intent": state["intent"],
                        "workflow": "destructive_query_langgraph",
                        "auto_approved": True
                    }
                )
                
                if temp_approval_result.get("status") != "success":
                    state["workflow_status"] = "error"
                    state["error_message"] = f"Failed to create temporary approval: {temp_approval_result.get('message')}"
                    return state
                
                # Immediately approve the temporary ticket
                temp_ticket_id = temp_approval_result.get("ticket_id")
                
                approval_update = await update_approval_status(
                    ticket_id=temp_ticket_id,
                    new_status="APPROVED",
                    approver_info={"approver": "system", "auto_approved": True},
                    comments="Auto-approved due to LOW/MEDIUM risk level"
                )
                
                if approval_update.get("status") != "success":
                    state["workflow_status"] = "error"
                    state["error_message"] = f"Failed to auto-approve temporary ticket: {approval_update.get('message')}"
                    return state
                
                # Execute the auto-approved query
                execution_result = await execute_approved_query(temp_ticket_id)
                
                # Store temporary ticket info for reference
                state["approval_ticket"] = temp_approval_result
            
            state["execution_result"] = execution_result
            
            if execution_result.get("status") == "success":
                state["workflow_status"] = "completed"
                logger.info("Destructive query executed successfully")
            else:
                state["workflow_status"] = "execution_failed"
                state["error_message"] = f"Query execution failed: {execution_result.get('message')}"
                logger.error(f"Query execution failed: {state['error_message']}")
            
        except Exception as e:
            state["workflow_status"] = "error"
            state["error_message"] = f"Query execution error: {str(e)}"
            logger.error(f"Error in execute_query_node: {e}")
        
        return state
    
    def _approval_router(self, state: DestructiveQueryState) -> str:
        """Route based on approval requirement"""
        if state.get("workflow_status") == "error":
            return "error"
        
        if state.get("approval_required", False):
            return "require_approval"
        else:
            return "auto_approve"
    
    def _approval_status_router(self, state: DestructiveQueryState) -> str:
        """Route based on approval status"""
        if state.get("workflow_status") == "error":
            return "error"
        
        approval_status = state.get("approval_status", "unknown")
        
        if approval_status == "approved":
            return "approved"
        elif approval_status == "rejected":
            return "rejected"
        elif approval_status == "expired":
            return "expired"
        elif approval_status in ["pending", "pending_approval"]:
            return "pending"
        else:
            return "error"
    
    async def run(self, user_query: str, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the destructive query workflow
        
        Args:
            user_query: Natural language query from user
            intent: Intent information from orchestrator
            
        Returns:
            Dict containing workflow results
        """
        try:
            logger.info(f"Starting destructive query workflow for {intent.get('type', 'UNKNOWN')} operation")
            
            # Initialize state
            initial_state = DestructiveQueryState(
                user_query=user_query,
                intent=intent,
                schema_context={},
                sql_query="",
                validation_result={},
                impact_analysis={},
                risk_level="UNKNOWN",
                approval_ticket={},
                approval_status="unknown",
                approval_required=False,
                execution_result={},
                workflow_status="running",
                error_message="",
                metadata={"workflow": "destructive_query", "started_at": "current_timestamp"}
            )
            
            # Run the workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            # Format response based on final state
            return self._format_response(final_state)
            
        except Exception as e:
            logger.error(f"Error running destructive query workflow: {e}")
            return {
                "status": "error",
                "message": f"Workflow execution failed: {str(e)}",
                "user_query": user_query,
                "intent": intent
            }
    
    def _format_response(self, state: DestructiveQueryState) -> Dict[str, Any]:
        """Format the workflow response"""
        workflow_status = state.get("workflow_status", "unknown")
        
        base_response = {
            "user_query": state.get("user_query", ""),
            "intent": state.get("intent", {}),
            "sql_query": state.get("sql_query", ""),
            "risk_level": state.get("risk_level", "UNKNOWN"),
            "workflow": "destructive_query",
            "metadata": state.get("metadata", {})
        }
        
        if workflow_status == "completed":
            # Successful execution
            execution_result = state.get("execution_result", {})
            return {
                **base_response,
                "status": "success",
                "message": "Destructive query executed successfully",
                "execution_result": execution_result,
                "approval_required": state.get("approval_required", False),
                "approval_ticket": state.get("approval_ticket", {}) if state.get("approval_required") else None
            }
        
        elif workflow_status == "running" and state.get("approval_required", False):
            # Waiting for approval
            return {
                **base_response,
                "status": "pending_approval",
                "message": f"Query requires approval due to {state.get('risk_level', 'UNKNOWN')} risk level",
                "approval_ticket": state.get("approval_ticket", {}),
                "impact_analysis": state.get("impact_analysis", {}),
                "next_steps": "Query is waiting for human approval. Use the ticket ID to approve or reject."
            }
        
        elif workflow_status == "execution_failed":
            # Execution failed
            return {
                **base_response,
                "status": "execution_failed",
                "message": state.get("error_message", "Query execution failed"),
                "execution_result": state.get("execution_result", {})
            }
        
        else:
            # Error or other status
            return {
                **base_response,
                "status": "error",
                "message": state.get("error_message", "Workflow failed"),
                "workflow_status": workflow_status
            }

# Create global workflow instance
destructive_query_workflow = DestructiveQueryWorkflow() 