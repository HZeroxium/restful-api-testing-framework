# server.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from infra.configs.app_config import settings
from infra.di.container import Container, get_container
from app.api.routers.endpoint_router import router as endpoint_router
from app.api.routers.constraint_router import router as constraint_router
from app.api.routers.validation_script_router import router as validation_script_router
from app.api.routers.dataset_router import router as dataset_router
from app.api.routers.verification_router import router as verification_router
from app.api.routers.aggregator_router import router as aggregator_router
from app.api.routers.test_data_router import router as test_data_router
from app.api.routers.execution_router import router as execution_router


# Setup logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configure the global container
container = get_container()
container.config.from_dict(
    {
        "endpoints": {"file_path": settings.endpoints_file_path},
        "constraints": {"file_path": settings.constraints_file_path},
        "validation_scripts": {"file_path": settings.validation_scripts_file_path},
        "datasets": {"base_path": settings.datasets_base_path},
    }
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting RESTful API Testing Framework...")
    logger.info(f"Application: {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")

    # Container is now configured with dependency functions
    # No need for wiring since we're using direct dependency functions
    logger.info("Dependency injection container configured successfully")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    # No unwiring needed since we're not using wiring anymore


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive RESTful API testing framework with multi-agent capabilities",
    debug=settings.debug,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dataset_router)
app.include_router(endpoint_router, prefix="/api/v1")
app.include_router(constraint_router, prefix="/api/v1")
app.include_router(validation_script_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(aggregator_router, prefix="/api/v1")
app.include_router(test_data_router, prefix="/api/v1")
app.include_router(execution_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    from fastapi.responses import JSONResponse

    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )
