"""
Health and system information API routes
"""

from fastapi import APIRouter, Request
from datetime import datetime
import os
import sys
from pathlib import Path

from ..models import HealthStatus, ConfigInfo, ApiResponse

router = APIRouter()


@router.get("/healthz", response_model=HealthStatus)
async def health_check():
    """Health check endpoint"""
    return HealthStatus(
        status="ok",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@router.get("/version", response_model=ApiResponse)
async def get_version():
    """Get version information"""
    try:
        # Try to get git commit if available
        git_commit = "unknown"
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], 
                capture_output=True, 
                text=True, 
                cwd=Path(__file__).parent.parent.parent
            )
            if result.returncode == 0:
                git_commit = result.stdout.strip()[:8]
        except:
            pass
        
        version_info = {
            "version": "1.0.0",
            "commit": git_commit,
            "python_version": sys.version,
            "build_date": datetime.now().isoformat()
        }
        
        return ApiResponse(
            success=True,
            message="Version information retrieved",
            data=version_info
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"Failed to get version: {str(e)}"
        )


@router.get("/config", response_model=ApiResponse)
async def get_config(request: Request):
    """Get configuration information"""
    try:
        db_manager = request.app.state.db
        
        config_info = ConfigInfo(
            database_path=str(db_manager.db_path),
            services_directory=str(db_manager.services_dir),
            working_directories={
                "database": str(db_manager.db_path.parent),
                "services": str(db_manager.services_dir),
                "project_root": str(Path(__file__).parent.parent.parent)
            }
        )
        
        return ApiResponse(
            success=True,
            message="Configuration retrieved",
            data=config_info.dict()
        )
    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"Failed to get config: {str(e)}"
        )
