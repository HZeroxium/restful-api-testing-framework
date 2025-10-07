"""
REST API Testing Framework Server
Main FastAPI application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import sys
from contextlib import asynccontextmanager

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.routes import services, test_cases, test_data, runs, health
from server.database import DatabaseManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and resources on startup"""
    db_manager = DatabaseManager()
    db_manager.initialize_database()
    app.state.db = db_manager
    yield
    # Cleanup on shutdown if needed


app = FastAPI(
    title="RESTful API Testing Framework",
    description="A comprehensive framework for testing RESTful APIs with test case generation and execution",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(services.router, prefix="/api/v1", tags=["Services"])
app.include_router(test_cases.router, prefix="/api/v1", tags=["Test Cases"])
app.include_router(test_data.router, prefix="/api/v1", tags=["Test Data"])
app.include_router(runs.router, prefix="/api/v1", tags=["Test Runs"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
