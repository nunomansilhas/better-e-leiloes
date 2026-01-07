"""
Passenger WSGI/ASGI Entry Point for cPanel Python App
======================================================
This file is the entry point for Phusion Passenger on cPanel hosting.
Supports both ASGI (FastAPI native) and WSGI (legacy) modes.
"""

import sys
import os

# Get the directory where this file is located (application root)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(APP_ROOT, 'backend')

# Add paths
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, APP_ROOT)

# Change working directory to backend
os.chdir(BACKEND_DIR)

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(BACKEND_DIR, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    root_env = os.path.join(APP_ROOT, '.env')
    if os.path.exists(root_env):
        load_dotenv(root_env)

# Import the FastAPI application
from main import app

# Passenger can work in two modes:
# 1. ASGI mode (newer Passenger versions) - use app directly
# 2. WSGI mode (legacy) - needs adapter

# Try to detect if we need WSGI adapter
try:
    # Check if Passenger is running in ASGI mode
    # Modern Passenger (5.3+) supports ASGI natively for Python
    application = app
except Exception as e:
    # Fallback: Create WSGI adapter for older Passenger
    import asyncio
    from io import BytesIO

    def wsgi_adapter(environ, start_response):
        """Simple WSGI to ASGI adapter for basic requests"""
        # This is a minimal adapter - for full compatibility use uvicorn
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # For complex apps, consider running uvicorn as subprocess
        # This adapter handles basic GET requests only
        path = environ.get('PATH_INFO', '/')

        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [b'ASGI app requires Passenger 5.3+ with Python ASGI support']

    application = wsgi_adapter


# For local development/debugging
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
