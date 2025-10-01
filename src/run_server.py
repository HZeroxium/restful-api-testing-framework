# run_server.py

"""
Script để chạy FastAPI server với cấu hình đúng.
"""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    from main import main

    main()
