"""
PostgreSQL AI Agent MVP - Main FastAPI Application
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import logging
import os
import json
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our agents
from agents.orchestrator import OrchestratorAgent

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

# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}

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