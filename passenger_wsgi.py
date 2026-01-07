"""
Passenger WSGI Entry Point for cPanel Python App
=================================================
FastAPI is ASGI, but cPanel's Passenger expects WSGI.
This file uses a2wsgi to bridge the two protocols.
"""

import sys
import os

# =============================================================================
# PATH SETUP - MUST BE FIRST
# =============================================================================

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(APP_ROOT, 'backend')

# Add paths to sys.path for imports
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, APP_ROOT)

# Change working directory to backend
os.chdir(BACKEND_DIR)

# =============================================================================
# SIMPLE DEBUG LOG
# =============================================================================

def log(msg):
    """Write to debug log"""
    try:
        with open(os.path.join(APP_ROOT, 'passenger_debug.log'), 'a') as f:
            from datetime import datetime
            f.write(f"{datetime.now()} - {msg}\n")
    except:
        pass

log("=" * 60)
log(f"Starting passenger_wsgi.py")
log(f"APP_ROOT: {APP_ROOT}")
log(f"BACKEND_DIR: {BACKEND_DIR}")
log(f"Python: {sys.executable}")
log(f"Python version: {sys.version}")

# =============================================================================
# LOAD ENVIRONMENT VARIABLES
# =============================================================================

try:
    from dotenv import load_dotenv
    env_path = os.path.join(BACKEND_DIR, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        log(f"Loaded .env from: {env_path}")
    log(f"DATABASE_URL set: {'DATABASE_URL' in os.environ}")
except ImportError as e:
    log(f"WARNING: python-dotenv not installed: {e}")
except Exception as e:
    log(f"ERROR loading .env: {e}")

# =============================================================================
# CREATE WSGI APPLICATION
# =============================================================================

application = None

try:
    log("Step 1: Importing FastAPI app...")
    from main import app as fastapi_app
    log("Step 1: SUCCESS - FastAPI app imported")

    log("Step 2: Importing a2wsgi...")
    from a2wsgi import ASGIMiddleware
    log("Step 2: SUCCESS - a2wsgi imported")

    log("Step 3: Creating WSGI application...")
    application = ASGIMiddleware(fastapi_app)
    log("Step 3: SUCCESS - WSGI application created!")
    log("=" * 60)

except ImportError as e:
    log(f"IMPORT ERROR: {e}")
    import traceback
    log(traceback.format_exc())

    # Fallback: simple error page
    def application(environ, start_response):
        status = '500 Internal Server Error'
        output = f'Import Error: {e}\n\nCheck passenger_debug.log for details.'.encode('utf-8')
        start_response(status, [('Content-type', 'text/plain'), ('Content-Length', str(len(output)))])
        return [output]

except Exception as e:
    log(f"UNEXPECTED ERROR: {e}")
    import traceback
    log(traceback.format_exc())

    # Fallback: simple error page
    def application(environ, start_response):
        status = '500 Internal Server Error'
        output = f'Error: {e}\n\nCheck passenger_debug.log for details.'.encode('utf-8')
        start_response(status, [('Content-type', 'text/plain'), ('Content-Length', str(len(output)))])
        return [output]

# =============================================================================
# LOCAL DEVELOPMENT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
