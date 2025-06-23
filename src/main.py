"""
PostgreSQL AI Agent MVP - Main FastAPI Application
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import logging
import os
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting PostgreSQL AI Agent MVP")
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
            
            # For now, echo back the query (will be replaced with actual processing)
            response = {
                "status": "received",
                "query": data,
                "message": "Query processing not yet implemented"
            }
            
            await websocket.send_json(response)
            
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