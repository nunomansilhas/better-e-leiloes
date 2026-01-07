"""
Passenger WSGI Entry Point for cPanel Python App
=================================================
FastAPI is ASGI, but cPanel's Passenger expects WSGI.
This file uses a2wsgi to bridge the two protocols.

IMPORTANT: Passenger calls this file and expects a `application` callable.
"""

import sys
import os
import logging
from datetime import datetime

# =============================================================================
# PATH SETUP
# =============================================================================

# Get the directory where this file is located (application root)
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(APP_ROOT, 'backend')

# Add paths to sys.path for imports
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, APP_ROOT)

# Change working directory to backend (where .env and modules are)
os.chdir(BACKEND_DIR)

# =============================================================================
# LOGGING SETUP (for debugging deployment issues)
# =============================================================================

log_file = os.path.join(APP_ROOT, 'passenger_debug.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info(f"Passenger WSGI starting at {datetime.now()}")
logger.info(f"APP_ROOT: {APP_ROOT}")
logger.info(f"BACKEND_DIR: {BACKEND_DIR}")
logger.info(f"Python: {sys.executable}")
logger.info(f"Python version: {sys.version}")
logger.info(f"sys.path: {sys.path[:5]}...")

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================

try:
    from dotenv import load_dotenv

    env_path = os.path.join(BACKEND_DIR, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Loaded .env from: {env_path}")
    else:
        root_env = os.path.join(APP_ROOT, '.env')
        if os.path.exists(root_env):
            load_dotenv(root_env)
            logger.info(f"Loaded .env from: {root_env}")
        else:
            logger.warning("No .env file found!")

    # Log important env vars (without secrets)
    logger.info(f"DATABASE_URL set: {'DATABASE_URL' in os.environ}")
    logger.info(f"API_SECRET_KEY set: {'API_SECRET_KEY' in os.environ}")

except Exception as e:
    logger.error(f"Error loading .env: {e}")

# =============================================================================
# ASGI -> WSGI ADAPTER
# =============================================================================

application = None

try:
    logger.info("Importing FastAPI application...")
    from main import app as fastapi_app
    logger.info("FastAPI app imported successfully")

    logger.info("Importing a2wsgi adapter...")
    from a2wsgi import ASGIMiddleware
    logger.info("a2wsgi imported successfully")

    # Create the WSGI-compatible application
    # ASGIMiddleware wraps the FastAPI app and handles the protocol conversion
    application = ASGIMiddleware(fastapi_app)
    logger.info("WSGI application created successfully!")

except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error(f"Module not found. Check if all dependencies are installed in virtualenv.")

    # Create a simple error response app
    def error_app(environ, start_response):
        status = '500 Internal Server Error'
        output = f'Import Error: {str(e)}\n\nCheck passenger_debug.log for details.'.encode('utf-8')
        response_headers = [
            ('Content-type', 'text/plain'),
            ('Content-Length', str(len(output)))
        ]
        start_response(status, response_headers)
        return [output]

    application = error_app

except Exception as e:
    logger.error(f"Unexpected error during setup: {e}")
    import traceback
    logger.error(traceback.format_exc())

    # Create a simple error response app
    def error_app(environ, start_response):
        status = '500 Internal Server Error'
        output = f'Setup Error: {str(e)}\n\nCheck passenger_debug.log for details.'.encode('utf-8')
        response_headers = [
            ('Content-type', 'text/plain'),
            ('Content-Length', str(len(output)))
        ]
        start_response(status, response_headers)
        return [output]

    application = error_app

logger.info("passenger_wsgi.py initialization complete")
logger.info("=" * 60)

# =============================================================================
# LOCAL DEVELOPMENT
# =============================================================================

if __name__ == "__main__":
    # For local testing, use uvicorn directly (native ASGI)
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
