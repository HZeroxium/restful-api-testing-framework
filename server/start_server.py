#!/usr/bin/env python3
"""
Start script for the RESTful API Testing Framework Server
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    # Change to server directory
    os.chdir(current_dir)
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
