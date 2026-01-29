import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Import the FastAPI app
from main import app

# For Passenger WSGI compatibility with ASGI apps
from starlette.middleware.wsgi import WSGIMiddleware

# Wrap ASGI app for WSGI (Passenger)
application = WSGIMiddleware(app)
