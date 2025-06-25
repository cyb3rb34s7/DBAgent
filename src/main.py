"""
PostgreSQL AI Agent MVP - Main FastAPI Application
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging
import os
import json
import traceback
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our agents
from agents.orchestrator import OrchestratorAgent

# Import approval workflow tools
from tools.impact_execution import update_approval_status, check_approval_status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global orchestrator agent instance
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global orchestrator
    logger.info("Starting PostgreSQL AI Agent MVP")
    
    # Initialize the orchestrator agent
    orchestrator = OrchestratorAgent()
    logger.info("OrchestratorAgent initialized")
    
    yield
    
    logger.info("Shutting down PostgreSQL AI Agent MVP")

# Initialize FastAPI app
app = FastAPI(
    title="PostgreSQL AI Agent MVP",
    description="AI-powered natural language to SQL agent with safety controls",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# P4.T1.1: Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler to catch unhandled errors and return standardized error responses
    
    Args:
        request: The incoming request
        exc: The unhandled exception
        
    Returns:
        JSONResponse with standardized error format
    """
    # Log the full exception with traceback for debugging
    logger.error(f"Unhandled exception on {request.method} {request.url}")
    logger.error(f"Exception: {exc}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Determine error type and status code
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        error_type = "http_error"
        message = exc.detail
    elif isinstance(exc, ValueError):
        status_code = 400
        error_type = "validation_error"
        message = f"Invalid input: {str(exc)}"
    elif isinstance(exc, ConnectionError):
        status_code = 503
        error_type = "connection_error"
        message = "Service temporarily unavailable"
    elif isinstance(exc, TimeoutError):
        status_code = 504
        error_type = "timeout_error"
        message = "Request timeout"
    else:
        status_code = 500
        error_type = "internal_error"
        message = "An unexpected error occurred"
    
    # Create standardized error response
    error_response = {
        "status": "error",
        "error_type": error_type,
        "message": message,
        "timestamp": "current_timestamp",
        "path": str(request.url),
        "method": request.method,
        "details": {
            "exception_class": exc.__class__.__name__,
            "exception_message": str(exc)
        }
    }
    
    # Add debug information in development
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    if debug_mode:
        error_response["debug"] = {
            "traceback": traceback.format_exc(),
            "request_headers": dict(request.headers)
        }
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )

# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}

# Approval workflow endpoints
@app.get("/approve/{ticket_id}")
async def approve_request(ticket_id: str, approver: str = "unknown", comments: str = None) -> Dict[str, Any]:
    """
    Approve a destructive query request
    
    Args:
        ticket_id: Unique ticket identifier
        approver: Name or ID of the approver (query parameter)
        comments: Optional approval comments (query parameter)
        
    Returns:
        Dict containing approval results
    """
    try:
        logger.info(f"Processing approval for ticket: {ticket_id}")
        
        # Check if ticket exists first
        status_check = await check_approval_status(ticket_id)
        if status_check.get("status") != "found":
            return {
                "status": "error",
                "message": status_check.get("message", "Ticket not found"),
                "ticket_id": ticket_id
            }
        
        # Update status to APPROVED
        approver_info = {
            "approver_id": approver,
            "approval_method": "web_endpoint",
            "ip_address": "unknown"  # In production, get from request
        }
        
        result = await update_approval_status(
            ticket_id, 
            "APPROVED", 
            approver_info, 
            comments
        )
        
        if result.get("status") == "success":
            logger.info(f"Ticket {ticket_id} approved by {approver}")
            return {
                "status": "success",
                "message": f"Request approved successfully",
                "ticket_id": ticket_id,
                "approver": approver,
                "approval_details": result
            }
        else:
            return {
                "status": "error",
                "message": result.get("message", "Failed to approve request"),
                "ticket_id": ticket_id
            }
            
    except Exception as e:
        logger.error(f"Error processing approval: {e}")
        return {
            "status": "error",
            "message": f"Approval processing failed: {str(e)}",
            "ticket_id": ticket_id
        }

@app.get("/reject/{ticket_id}")
async def reject_request(ticket_id: str, approver: str = "unknown", comments: str = None) -> Dict[str, Any]:
    """
    Reject a destructive query request
    
    Args:
        ticket_id: Unique ticket identifier
        approver: Name or ID of the approver (query parameter)
        comments: Optional rejection comments (query parameter)
        
    Returns:
        Dict containing rejection results
    """
    try:
        logger.info(f"Processing rejection for ticket: {ticket_id}")
        
        # Check if ticket exists first
        status_check = await check_approval_status(ticket_id)
        if status_check.get("status") != "found":
            return {
                "status": "error",
                "message": status_check.get("message", "Ticket not found"),
                "ticket_id": ticket_id
            }
        
        # Update status to REJECTED
        approver_info = {
            "approver_id": approver,
            "approval_method": "web_endpoint",
            "ip_address": "unknown"  # In production, get from request
        }
        
        result = await update_approval_status(
            ticket_id, 
            "REJECTED", 
            approver_info, 
            comments
        )
        
        if result.get("status") == "success":
            logger.info(f"Ticket {ticket_id} rejected by {approver}")
            return {
                "status": "success",
                "message": f"Request rejected successfully",
                "ticket_id": ticket_id,
                "approver": approver,
                "rejection_details": result
            }
        else:
            return {
                "status": "error",
                "message": result.get("message", "Failed to reject request"),
                "ticket_id": ticket_id
            }
            
    except Exception as e:
        logger.error(f"Error processing rejection: {e}")
        return {
            "status": "error",
            "message": f"Rejection processing failed: {str(e)}",
            "ticket_id": ticket_id
        }

@app.get("/status/{ticket_id}")
async def get_ticket_status(ticket_id: str) -> Dict[str, Any]:
    """
    Get the status of an approval request
    
    Args:
        ticket_id: Unique ticket identifier
        
    Returns:
        Dict containing ticket status and details
    """
    try:
        logger.info(f"Getting status for ticket: {ticket_id}")
        
        result = await check_approval_status(ticket_id)
        
        if result.get("status") == "found":
            return {
                "status": "success",
                "ticket_id": ticket_id,
                "approval_status": result.get("approval_status"),
                "message": result.get("message"),
                "time_remaining": result.get("time_remaining"),
                "is_approved": result.get("is_approved"),
                "is_rejected": result.get("is_rejected"),
                "request_details": result.get("approval_request", {})
            }
        else:
            return {
                "status": result.get("status", "error"),
                "message": result.get("message", "Unknown error"),
                "ticket_id": ticket_id
            }
            
    except Exception as e:
        logger.error(f"Error getting ticket status: {e}")
        return {
            "status": "error",
            "message": f"Status check failed: {str(e)}",
            "ticket_id": ticket_id
        }

# WebSocket endpoint for real-time query communication
@app.websocket("/ws/query")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time query processing"""
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received query: {data}")
            
            # Process the query using the orchestrator agent
            try:
                response = await orchestrator.process_query(data)
                logger.info(f"Orchestrator response: {response}")
                
                # Send the response back to the client
                await websocket.send_json(response)
                
            except Exception as e:
                logger.error(f"Error processing query: {e}")
                error_response = {
                    "status": "error",
                    "message": f"Failed to process query: {str(e)}",
                    "query": data
                }
                await websocket.send_json(error_response)
            
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    
    # Load environment variables
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=debug,
        log_level="info"
    ) 