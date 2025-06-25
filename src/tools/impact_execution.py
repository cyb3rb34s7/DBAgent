"""
PostgreSQL AI Agent MVP - Impact Analysis and Execution Tools
MCP Server 2: Impact analysis, approval workflow, and safe execution
"""

import psycopg2
import psycopg2.extras
from typing import Dict, Any, List, Optional
import logging
import os
from contextlib import contextmanager
from dotenv import load_dotenv
from agents.impact_analysis import get_impact_analysis_agent

# Load environment variables from .env file
load_dotenv()

# Additional imports for approval workflow
import uuid
import json
from datetime import datetime, timedelta
from utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)

class ImpactExecutionOperations:
    """Impact analysis and safe execution operations handler"""
    
    def __init__(self):
        """Initialize impact and execution operations"""
        self.connection_string = os.getenv("DATABASE_URL")
        if not self.connection_string:
            logger.warning("DATABASE_URL not set, using default connection parameters")
            self.connection_string = "postgresql://postgres:password@localhost:5432/postgres"
        else:
            logger.info("DATABASE_URL loaded from environment")
        
        # Initialize impact analysis agent
        self.impact_agent = get_impact_analysis_agent()
        
        # Initialize Redis client for approval workflow
        self.redis_client = get_redis_client()
        
        logger.info("ImpactExecutionOperations initialized")
    
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
    
    async def analyze_query_impact(self, sql_query: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the potential impact of a destructive SQL query using EXPLAIN
        
        Args:
            sql_query: The SQL query to analyze (UPDATE/DELETE/INSERT)
            intent_data: Intent information from orchestrator
            
        Returns:
            Dict containing comprehensive impact analysis
        """
        try:
            logger.info(f"Analyzing query impact: {sql_query[:100]}...")
            
            # Step 1: Use Impact Analysis Agent for comprehensive analysis
            impact_analysis = await self.impact_agent.analyze_query_impact(sql_query, intent_data)
            
            if impact_analysis.get("status") != "success":
                return impact_analysis
            
            # Step 2: Enhance with database-level EXPLAIN analysis
            explain_analysis = await self._get_explain_analysis(sql_query)
            
            # Step 3: Combine results
            combined_analysis = {
                **impact_analysis,
                "explain_analysis": explain_analysis,
                "analysis_method": "combined_agent_and_explain",
                "timestamp": "current_timestamp"
            }
            
            # Update impact estimate with EXPLAIN data if available
            if explain_analysis.get("status") == "success":
                explain_rows = explain_analysis.get("estimated_rows")
                if explain_rows is not None:
                    # Use EXPLAIN estimate if available (more accurate)
                    combined_analysis["impact_estimate"]["estimated_rows"] = explain_rows
                    combined_analysis["impact_estimate"]["method"] = "explain_analyze"
                    combined_analysis["impact_estimate"]["confidence"] = "high"
                    
                    # Re-classify risk with accurate row count
                    risk_classification = self.impact_agent._classify_risk(
                        combined_analysis["impact_estimate"],
                        combined_analysis["query_type"],
                        combined_analysis["affected_tables"]
                    )
                    combined_analysis["risk_classification"] = risk_classification
            
            logger.info(f"Impact analysis completed: {combined_analysis['risk_classification']['level']} risk")
            return combined_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing query impact: {e}")
            return {
                "status": "error",
                "message": f"Impact analysis failed: {str(e)}",
                "error_type": "analysis_error"
            }
    
    async def _get_explain_analysis(self, sql_query: str) -> Dict[str, Any]:
        """
        Get EXPLAIN analysis for the query to estimate actual impact
        
        Args:
            sql_query: SQL query to analyze
            
        Returns:
            Dict containing EXPLAIN analysis results
        """
        try:
            # For destructive queries, we need to convert to SELECT for EXPLAIN
            explain_query = self._convert_to_explain_query(sql_query)
            
            if not explain_query:
                return {
                    "status": "error",
                    "message": "Could not convert query for EXPLAIN analysis"
                }
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Execute EXPLAIN to get query plan
                    cursor.execute(f"EXPLAIN (FORMAT JSON) {explain_query}")
                    explain_result = cursor.fetchone()
                    
                    if explain_result and explain_result[0]:
                        plan = explain_result[0][0]  # Get the plan from JSON result
                        
                        # Extract relevant information from the plan
                        estimated_rows = self._extract_rows_from_plan(plan)
                        estimated_cost = plan.get("Total Cost", 0)
                        
                        return {
                            "status": "success",
                            "explain_query": explain_query,
                            "estimated_rows": estimated_rows,
                            "estimated_cost": estimated_cost,
                            "plan_details": plan,
                            "method": "postgresql_explain"
                        }
                    else:
                        return {
                            "status": "error",
                            "message": "No EXPLAIN result returned"
                        }
                        
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error in EXPLAIN analysis: {e}")
            return {
                "status": "error",
                "message": f"Database error: {str(e)}",
                "error_type": "database_error"
            }
        except Exception as e:
            logger.error(f"Error in EXPLAIN analysis: {e}")
            return {
                "status": "error",
                "message": f"EXPLAIN analysis failed: {str(e)}",
                "error_type": "system_error"
            }
    
    def _convert_to_explain_query(self, sql_query: str) -> Optional[str]:
        """
        Convert destructive query to equivalent SELECT for EXPLAIN analysis
        
        Args:
            sql_query: Original destructive query
            
        Returns:
            Equivalent SELECT query for EXPLAIN, or None if conversion fails
        """
        query_upper = sql_query.strip().upper()
        
        try:
            if query_upper.startswith('UPDATE'):
                # Convert UPDATE to SELECT: UPDATE table SET ... WHERE ... -> SELECT * FROM table WHERE ...
                parts = sql_query.split()
                if len(parts) < 2:
                    return None
                
                table_name = parts[1]
                
                # Find WHERE clause if it exists
                where_index = -1
                for i, part in enumerate(parts):
                    if part.upper() == 'WHERE':
                        where_index = i
                        break
                
                if where_index > 0:
                    where_clause = ' '.join(parts[where_index:])
                    return f"SELECT * FROM {table_name} {where_clause}"
                else:
                    return f"SELECT * FROM {table_name}"
            
            elif query_upper.startswith('DELETE'):
                # Convert DELETE to SELECT: DELETE FROM table WHERE ... -> SELECT * FROM table WHERE ...
                if 'FROM' in query_upper:
                    # Replace DELETE with SELECT *
                    return sql_query.replace('DELETE', 'SELECT *', 1)
                else:
                    return None
            
            elif query_upper.startswith('INSERT'):
                # For INSERT, we can't easily estimate rows without knowing the data
                # Return None to indicate EXPLAIN analysis not applicable
                return None
            
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error converting query for EXPLAIN: {e}")
            return None
    
    def _extract_rows_from_plan(self, plan: Dict[str, Any]) -> Optional[int]:
        """
        Extract estimated row count from PostgreSQL query plan
        
        Args:
            plan: PostgreSQL query plan dictionary
            
        Returns:
            Estimated number of rows, or None if not available
        """
        try:
            # Try to get rows from different plan node types
            if "Plan Rows" in plan:
                return int(plan["Plan Rows"])
            elif "Rows" in plan:
                return int(plan["Rows"])
            
            # If not found at top level, check child plans
            if "Plans" in plan and plan["Plans"]:
                for child_plan in plan["Plans"]:
                    rows = self._extract_rows_from_plan(child_plan)
                    if rows is not None:
                        return rows
            
            return None
            
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error extracting rows from plan: {e}")
            return None
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test database connection for impact analysis
        
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
                        "message": "Impact analysis database connection successful",
                        "database_version": version
                    }
                    
        except Exception as e:
            logger.error(f"Impact analysis database connection test failed: {e}")
            return {
                "status": "error",
                "message": f"Database connection failed: {str(e)}",
                "error_type": "connection_error"
            }
    
    async def create_approval_request(self, sql_query: str, impact_analysis: Dict[str, Any], 
                                    requester_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create an approval request and store it in Redis with unique ticket ID
        
        Args:
            sql_query: The SQL query requiring approval
            impact_analysis: Complete impact analysis results
            requester_info: Information about the requester (optional)
            
        Returns:
            Dict containing approval request details
        """
        try:
            logger.info("Creating approval request for destructive query")
            
            # Generate unique ticket ID
            ticket_id = str(uuid.uuid4())
            
            # Create approval request data
            approval_request = {
                "ticket_id": ticket_id,
                "status": "PENDING_APPROVAL",
                "sql_query": sql_query,
                "impact_analysis": impact_analysis,
                "requester_info": requester_info or {},
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),  # 24 hour expiry
                "approval_history": [],
                "metadata": {
                    "risk_level": impact_analysis.get("risk_classification", {}).get("level", "UNKNOWN"),
                    "estimated_rows": impact_analysis.get("impact_estimate", {}).get("estimated_rows", "unknown"),
                    "affected_tables": impact_analysis.get("affected_tables", []),
                    "requires_approval": impact_analysis.get("risk_classification", {}).get("requires_approval", True)
                }
            }
            
            # Store in Redis with 24-hour TTL
            if self.redis_client.is_connected():
                redis_key = f"approval_request:{ticket_id}"
                success = self.redis_client.redis_client.setex(
                    redis_key, 
                    86400,  # 24 hours in seconds
                    json.dumps(approval_request, default=str)
                )
                
                if success:
                    logger.info(f"Approval request created with ticket ID: {ticket_id}")
                    return {
                        "status": "success",
                        "ticket_id": ticket_id,
                        "approval_request": approval_request,
                        "message": f"Approval request created. Ticket ID: {ticket_id}",
                        "expires_in_hours": 24
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Failed to store approval request in Redis",
                        "error_type": "storage_error"
                    }
            else:
                return {
                    "status": "error",
                    "message": "Redis not available for approval workflow",
                    "error_type": "redis_unavailable"
                }
                
        except Exception as e:
            logger.error(f"Error creating approval request: {e}")
            return {
                "status": "error",
                "message": f"Failed to create approval request: {str(e)}",
                "error_type": "creation_error"
            }
    
    async def check_approval_status(self, ticket_id: str) -> Dict[str, Any]:
        """
        Check the approval status of a ticket in Redis
        
        Args:
            ticket_id: Unique ticket identifier
            
        Returns:
            Dict containing approval status and details
        """
        try:
            logger.info(f"Checking approval status for ticket: {ticket_id}")
            
            if not self.redis_client.is_connected():
                return {
                    "status": "error",
                    "message": "Redis not available for approval workflow",
                    "error_type": "redis_unavailable"
                }
            
            # Retrieve approval request from Redis
            redis_key = f"approval_request:{ticket_id}"
            request_data = self.redis_client.redis_client.get(redis_key)
            
            if not request_data:
                return {
                    "status": "not_found",
                    "message": f"Approval request not found or expired: {ticket_id}",
                    "ticket_id": ticket_id
                }
            
            # Parse the stored data
            approval_request = json.loads(request_data)
            
            # Check if request has expired
            expires_at = datetime.fromisoformat(approval_request.get("expires_at", ""))
            if datetime.utcnow() > expires_at:
                # Mark as expired and remove from Redis
                self.redis_client.redis_client.delete(redis_key)
                return {
                    "status": "expired",
                    "message": f"Approval request expired: {ticket_id}",
                    "ticket_id": ticket_id,
                    "expired_at": approval_request.get("expires_at")
                }
            
            # Return current status
            current_status = approval_request.get("status", "UNKNOWN")
            
            return {
                "status": "found",
                "ticket_id": ticket_id,
                "approval_status": current_status,
                "approval_request": approval_request,
                "message": f"Approval request status: {current_status}",
                "time_remaining": str(expires_at - datetime.utcnow()),
                "is_approved": current_status == "APPROVED",
                "is_rejected": current_status == "REJECTED"
            }
            
        except Exception as e:
            logger.error(f"Error checking approval status: {e}")
            return {
                "status": "error",
                "message": f"Failed to check approval status: {str(e)}",
                "error_type": "check_error",
                "ticket_id": ticket_id
            }
    
    async def update_approval_status(self, ticket_id: str, new_status: str, 
                                   approver_info: Dict[str, Any] = None, 
                                   comments: str = None) -> Dict[str, Any]:
        """
        Update the approval status of a ticket (internal method for FastAPI endpoint)
        
        Args:
            ticket_id: Unique ticket identifier
            new_status: New status (APPROVED, REJECTED, etc.)
            approver_info: Information about the approver
            comments: Optional approval comments
            
        Returns:
            Dict containing update results
        """
        try:
            logger.info(f"Updating approval status for ticket {ticket_id} to {new_status}")
            
            if not self.redis_client.is_connected():
                return {
                    "status": "error",
                    "message": "Redis not available for approval workflow",
                    "error_type": "redis_unavailable"
                }
            
            # Check if ticket exists
            status_check = await self.check_approval_status(ticket_id)
            if status_check.get("status") != "found":
                return status_check
            
            # Get current approval request
            approval_request = status_check.get("approval_request", {})
            
            # Update status and add to history
            old_status = approval_request.get("status")
            approval_request["status"] = new_status
            approval_request["updated_at"] = datetime.utcnow().isoformat()
            
            # Add to approval history
            history_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "old_status": old_status,
                "new_status": new_status,
                "approver_info": approver_info or {},
                "comments": comments
            }
            approval_request["approval_history"].append(history_entry)
            
            # Store updated request back in Redis
            redis_key = f"approval_request:{ticket_id}"
            success = self.redis_client.redis_client.setex(
                redis_key,
                86400,  # Keep 24-hour TTL
                json.dumps(approval_request, default=str)
            )
            
            if success:
                logger.info(f"Approval status updated: {ticket_id} -> {new_status}")
                return {
                    "status": "success",
                    "ticket_id": ticket_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "approval_request": approval_request,
                    "message": f"Approval status updated to {new_status}"
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to update approval status in Redis",
                    "error_type": "storage_error"
                }
                
        except Exception as e:
            logger.error(f"Error updating approval status: {e}")
            return {
                "status": "error",
                "message": f"Failed to update approval status: {str(e)}",
                "error_type": "update_error",
                "ticket_id": ticket_id
            }
    
    async def execute_approved_query(self, ticket_id: str, executor_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute an approved destructive query with transaction safety
        
        Args:
            ticket_id: Unique ticket identifier for the approved request
            executor_info: Information about the person executing the query
            
        Returns:
            Dict containing execution results
        """
        try:
            logger.info(f"Executing approved query for ticket: {ticket_id}")
            
            # Step 1: Verify ticket exists and is approved
            status_check = await self.check_approval_status(ticket_id)
            
            if status_check.get("status") != "found":
                return {
                    "status": "error",
                    "message": f"Ticket not found: {status_check.get('message')}",
                    "ticket_id": ticket_id,
                    "error_type": "ticket_not_found"
                }
            
            approval_request = status_check.get("approval_request", {})
            current_status = approval_request.get("status")
            
            if current_status != "APPROVED":
                return {
                    "status": "error",
                    "message": f"Query not approved. Current status: {current_status}",
                    "ticket_id": ticket_id,
                    "current_status": current_status,
                    "error_type": "not_approved"
                }
            
            # Step 2: Get the SQL query and metadata
            sql_query = approval_request.get("sql_query")
            if not sql_query:
                return {
                    "status": "error",
                    "message": "No SQL query found in approval request",
                    "ticket_id": ticket_id,
                    "error_type": "missing_query"
                }
            
            # Step 3: Final safety validation
            query_type = self._get_query_type(sql_query)
            if query_type not in ["UPDATE", "DELETE", "INSERT"]:
                return {
                    "status": "error",
                    "message": f"Invalid query type for safe execution: {query_type}",
                    "ticket_id": ticket_id,
                    "query_type": query_type,
                    "error_type": "invalid_query_type"
                }
            
            # Step 4: Execute query with transaction safety
            execution_result = await self._execute_with_transaction(sql_query, ticket_id, executor_info)
            
            # Step 5: Update ticket status to EXECUTED
            if execution_result.get("status") == "success":
                await self.update_approval_status(
                    ticket_id,
                    "EXECUTED",
                    executor_info or {},
                    f"Query executed successfully. Rows affected: {execution_result.get('rows_affected', 'unknown')}"
                )
            else:
                await self.update_approval_status(
                    ticket_id,
                    "EXECUTION_FAILED",
                    executor_info or {},
                    f"Query execution failed: {execution_result.get('message', 'unknown error')}"
                )
            
            return {
                **execution_result,
                "ticket_id": ticket_id,
                "executed_by": executor_info,
                "approval_request": approval_request
            }
            
        except Exception as e:
            logger.error(f"Error executing approved query: {e}")
            
            # Try to update ticket status to indicate execution failure
            try:
                await self.update_approval_status(
                    ticket_id,
                    "EXECUTION_ERROR",
                    executor_info or {},
                    f"Execution error: {str(e)}"
                )
            except:
                pass  # Don't fail if we can't update status
            
            return {
                "status": "error",
                "message": f"Query execution failed: {str(e)}",
                "ticket_id": ticket_id,
                "error_type": "execution_error"
            }
    
    async def _execute_with_transaction(self, sql_query: str, ticket_id: str, 
                                      executor_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute destructive query within a transaction with rollback capability
        
        Args:
            sql_query: SQL query to execute
            ticket_id: Ticket ID for logging
            executor_info: Executor information for logging
            
        Returns:
            Dict containing execution results
        """
        connection = None
        try:
            logger.info(f"Starting transaction for ticket {ticket_id}")
            
            # Get database connection
            connection = psycopg2.connect(self.connection_string)
            connection.autocommit = False  # Ensure manual transaction control
            
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Begin transaction explicitly
                cursor.execute("BEGIN")
                logger.info("Transaction started")
                
                # Log the execution attempt
                logger.info(f"Executing: {sql_query[:100]}...")
                
                # Execute the destructive query
                cursor.execute(sql_query)
                
                # Get number of affected rows
                rows_affected = cursor.rowcount
                logger.info(f"Query executed, {rows_affected} rows affected")
                
                # For SELECT queries that might be part of the destructive operation,
                # we might want to fetch results
                results = []
                if sql_query.strip().upper().startswith('SELECT'):
                    results = [dict(row) for row in cursor.fetchall()]
                
                # Commit the transaction
                cursor.execute("COMMIT")
                connection.commit()
                logger.info(f"Transaction committed successfully for ticket {ticket_id}")
                
                return {
                    "status": "success",
                    "message": f"Query executed successfully. {rows_affected} rows affected.",
                    "rows_affected": rows_affected,
                    "results": results,
                    "sql_query": sql_query,
                    "execution_method": "transaction_safe",
                    "transaction_status": "committed"
                }
                
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error during execution: {e}")
            
            # Rollback transaction
            if connection:
                try:
                    connection.rollback()
                    logger.info(f"Transaction rolled back for ticket {ticket_id}")
                    rollback_status = "rolled_back"
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                    rollback_status = "rollback_failed"
            else:
                rollback_status = "no_connection"
            
            return {
                "status": "error",
                "message": f"Database error: {str(e)}",
                "error_type": "database_error",
                "sql_query": sql_query,
                "execution_method": "transaction_safe",
                "transaction_status": rollback_status
            }
            
        except Exception as e:
            logger.error(f"Unexpected error during execution: {e}")
            
            # Rollback transaction
            if connection:
                try:
                    connection.rollback()
                    logger.info(f"Transaction rolled back for ticket {ticket_id}")
                    rollback_status = "rolled_back"
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                    rollback_status = "rollback_failed"
            else:
                rollback_status = "no_connection"
            
            return {
                "status": "error",
                "message": f"Execution error: {str(e)}",
                "error_type": "system_error",
                "sql_query": sql_query,
                "execution_method": "transaction_safe",
                "transaction_status": rollback_status
            }
            
        finally:
            # Always close the connection
            if connection:
                connection.close()
                logger.info("Database connection closed")
    
    def _get_query_type(self, sql_query: str) -> str:
        """Extract query type from SQL query"""
        query_upper = sql_query.strip().upper()
        
        if query_upper.startswith('UPDATE'):
            return "UPDATE"
        elif query_upper.startswith('DELETE'):
            return "DELETE"
        elif query_upper.startswith('INSERT'):
            return "INSERT"
        elif query_upper.startswith('SELECT'):
            return "SELECT"
        else:
            return "UNKNOWN"
    
    async def rollback_operation(self, ticket_id: str, operation_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        P4.T1.3: Rollback operation tool as a fallback mechanism
        
        Args:
            ticket_id: Unique ticket identifier for the operation to rollback
            operation_info: Information about the operation to rollback
            
        Returns:
            Dict containing rollback results
        """
        try:
            logger.warning(f"Rollback operation requested for ticket: {ticket_id}")
            
            # Step 1: Log the rollback request
            rollback_info = {
                "ticket_id": ticket_id,
                "rollback_requested_at": datetime.utcnow().isoformat(),
                "operation_info": operation_info or {},
                "rollback_method": "logging_fallback",
                "status": "logged"
            }
            
            # Step 2: Try to get the original approval request for context
            try:
                status_check = await self.check_approval_status(ticket_id)
                if status_check.get("status") == "found":
                    approval_request = status_check.get("approval_request", {})
                    rollback_info["original_query"] = approval_request.get("sql_query", "unknown")
                    rollback_info["risk_level"] = approval_request.get("metadata", {}).get("risk_level", "unknown")
                    rollback_info["affected_tables"] = approval_request.get("metadata", {}).get("affected_tables", [])
            except Exception as e:
                logger.error(f"Could not retrieve original request info for rollback: {e}")
                rollback_info["retrieval_error"] = str(e)
            
            # Step 3: Log detailed rollback information
            logger.critical(f"ROLLBACK OPERATION LOGGED:")
            logger.critical(f"  Ticket ID: {ticket_id}")
            logger.critical(f"  Original Query: {rollback_info.get('original_query', 'unknown')}")
            logger.critical(f"  Risk Level: {rollback_info.get('risk_level', 'unknown')}")
            logger.critical(f"  Affected Tables: {rollback_info.get('affected_tables', [])}")
            logger.critical(f"  Rollback Reason: {operation_info.get('reason', 'not specified')}")
            logger.critical(f"  Requested By: {operation_info.get('requested_by', 'system')}")
            
            # Step 4: Store rollback log in Redis for audit trail
            if self.redis_client.is_connected():
                try:
                    redis_key = f"rollback_log:{ticket_id}"
                    success = self.redis_client.redis_client.setex(
                        redis_key, 
                        604800,  # 7 days in seconds
                        json.dumps(rollback_info, default=str)
                    )
                    
                    if success:
                        logger.info(f"Rollback log stored in Redis for ticket {ticket_id}")
                        rollback_info["redis_logged"] = True
                    else:
                        logger.warning(f"Failed to store rollback log in Redis for ticket {ticket_id}")
                        rollback_info["redis_logged"] = False
                except Exception as e:
                    logger.error(f"Error storing rollback log in Redis: {e}")
                    rollback_info["redis_error"] = str(e)
                    rollback_info["redis_logged"] = False
            else:
                rollback_info["redis_logged"] = False
                logger.warning("Redis not available for rollback logging")
            
            # Step 5: Generate rollback recommendations
            rollback_recommendations = self._generate_rollback_recommendations(rollback_info)
            rollback_info["recommendations"] = rollback_recommendations
            
            # Step 6: Update ticket status to indicate rollback requested
            try:
                await self.update_approval_status(
                    ticket_id,
                    "ROLLBACK_REQUESTED",
                    operation_info or {},
                    f"Rollback operation logged. Manual intervention required."
                )
                rollback_info["ticket_updated"] = True
            except Exception as e:
                logger.error(f"Could not update ticket status for rollback: {e}")
                rollback_info["ticket_update_error"] = str(e)
                rollback_info["ticket_updated"] = False
            
            return {
                "status": "logged",
                "message": "Rollback operation has been logged. Manual intervention required for actual rollback.",
                "ticket_id": ticket_id,
                "rollback_info": rollback_info,
                "action_required": "Manual database rollback or restore from backup may be needed",
                "contact": "Database administrator should be contacted immediately"
            }
            
        except Exception as e:
            logger.error(f"Error in rollback operation: {e}")
            return {
                "status": "error",
                "message": f"Rollback operation failed: {str(e)}",
                "ticket_id": ticket_id,
                "error_type": "rollback_error"
            }
    
    def _generate_rollback_recommendations(self, rollback_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate rollback recommendations based on the operation
        
        Args:
            rollback_info: Information about the rollback request
            
        Returns:
            Dict containing rollback recommendations
        """
        recommendations = {
            "immediate_actions": [],
            "rollback_strategies": [],
            "prevention_measures": [],
            "escalation_required": False
        }
        
        risk_level = rollback_info.get("risk_level", "unknown").upper()
        original_query = rollback_info.get("original_query", "").upper()
        
        # Risk-based recommendations
        if risk_level in ["HIGH", "CRITICAL"]:
            recommendations["escalation_required"] = True
            recommendations["immediate_actions"].extend([
                "Notify database administrator immediately",
                "Stop all related operations",
                "Assess data integrity impact"
            ])
        
        # Query-type specific recommendations
        if "DELETE" in original_query:
            recommendations["rollback_strategies"].extend([
                "Restore deleted data from most recent backup",
                "Check if soft delete option is available",
                "Verify referential integrity after restore"
            ])
        elif "UPDATE" in original_query:
            recommendations["rollback_strategies"].extend([
                "Restore original values from backup",
                "Use transaction log to identify changed records",
                "Consider point-in-time recovery if available"
            ])
        elif "INSERT" in original_query:
            recommendations["rollback_strategies"].extend([
                "Delete inserted records using primary keys",
                "Check for cascade effects on related tables",
                "Verify constraint violations after cleanup"
            ])
        
        # General prevention measures
        recommendations["prevention_measures"].extend([
            "Review approval workflow for this type of operation",
            "Implement additional validation checks",
            "Consider requiring backup verification before execution",
            "Add rollback testing to approval process"
        ])
        
        return recommendations

# Global instance
impact_ops = ImpactExecutionOperations()

# Convenience functions for tools
async def analyze_query_impact(sql_query: str, intent_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze query impact - tool function"""
    return await impact_ops.analyze_query_impact(sql_query, intent_data)

async def test_impact_connection() -> Dict[str, Any]:
    """Test impact analysis database connection - tool function"""
    return await impact_ops.test_connection()

async def create_approval_request(sql_query: str, impact_analysis: Dict[str, Any], 
                                requester_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create approval request - tool function"""
    return await impact_ops.create_approval_request(sql_query, impact_analysis, requester_info)

async def check_approval_status(ticket_id: str) -> Dict[str, Any]:
    """Check approval status - tool function"""
    return await impact_ops.check_approval_status(ticket_id)

async def update_approval_status(ticket_id: str, new_status: str, 
                               approver_info: Dict[str, Any] = None, 
                               comments: str = None) -> Dict[str, Any]:
    """Update approval status - tool function"""
    return await impact_ops.update_approval_status(ticket_id, new_status, approver_info, comments)

async def execute_approved_query(ticket_id: str, executor_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """Execute approved query - tool function"""
    return await impact_ops.execute_approved_query(ticket_id, executor_info)

async def rollback_operation(ticket_id: str, operation_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """Rollback operation - tool function (P4.T1.3)"""
    return await impact_ops.rollback_operation(ticket_id, operation_info) 