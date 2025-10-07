#!/usr/bin/env python3
"""
Simple HTTP server to serve the RESTful API Testing Framework Frontend
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

# Configuration
PORT = 8081
HOST = 'localhost'

def main():
    # Change to frontend directory
    frontend_dir = Path(__file__).parent
    os.chdir(frontend_dir)
    
    print(f"RESTful API Testing Framework - Frontend Server")
    print(f"{'=' * 50}")
    print(f"Starting server on http://{HOST}:{PORT}")
    print(f"Serving files from: {frontend_dir}")
    print(f"{'=' * 50}")
    
    # Create HTTP request handler
    handler = http.server.SimpleHTTPRequestHandler
    
    # Create server
    try:
        with socketserver.TCPServer((HOST, PORT), handler) as httpd:
            print(f"✅ Server started successfully!")
            print(f"📂 Frontend: http://{HOST}:{PORT}")
            print(f"🔗 Backend API should be running on: http://localhost:8000")
            print(f"\n🚀 Opening browser...")
            
            # Open browser
            try:
                webbrowser.open(f'http://{HOST}:{PORT}')
            except Exception as e:
                print(f"⚠️  Could not open browser automatically: {e}")
                print(f"   Please open http://{HOST}:{PORT} manually")
            
            print(f"\n🔄 Server is running. Press Ctrl+C to stop.")
            print(f"{'=' * 50}")
            
            # Start serving
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped by user")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Error: Port {PORT} is already in use")
            print(f"   Try using a different port or stop the existing server")
            print(f"   Alternative command: python -m http.server {PORT + 1}")
        else:
            print(f"❌ Error starting server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
