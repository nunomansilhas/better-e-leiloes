import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Enable nested event loops (fixes async issues with Passenger)
import nest_asyncio
nest_asyncio.apply()

# Import the FastAPI app
from main import app

# Use TestClient for proper async handling with Passenger WSGI
from starlette.testclient import TestClient

# CORS headers to add to all responses
CORS_HEADERS = [
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
    ('Access-Control-Allow-Headers', '*'),
]


def application(environ, start_response):
    """WSGI application wrapper for FastAPI"""
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')
    query = environ.get('QUERY_STRING', '')

    # Build full path with query string
    full_path = f"{path}?{query}" if query else path

    # Get request headers
    headers = {}
    for key, value in environ.items():
        if key.startswith('HTTP_'):
            header_name = key[5:].replace('_', '-').title()
            headers[header_name] = value
        elif key == 'CONTENT_TYPE':
            headers['Content-Type'] = value
        elif key == 'CONTENT_LENGTH':
            headers['Content-Length'] = value

    try:
        # Create a fresh TestClient for each request to avoid concurrency issues
        with TestClient(app, raise_server_exceptions=False) as client:
            # Route request based on method
            if method == 'GET':
                response = client.get(full_path, headers=headers)
            elif method == 'POST':
                content_length = int(environ.get('CONTENT_LENGTH', 0) or 0)
                body = environ['wsgi.input'].read(content_length) if content_length > 0 else b''
                content_type = environ.get('CONTENT_TYPE', 'application/json')
                response = client.post(full_path, content=body, headers={**headers, 'Content-Type': content_type})
            elif method == 'PUT':
                content_length = int(environ.get('CONTENT_LENGTH', 0) or 0)
                body = environ['wsgi.input'].read(content_length) if content_length > 0 else b''
                content_type = environ.get('CONTENT_TYPE', 'application/json')
                response = client.put(full_path, content=body, headers={**headers, 'Content-Type': content_type})
            elif method == 'DELETE':
                response = client.delete(full_path, headers=headers)
            elif method == 'OPTIONS':
                # Handle CORS preflight directly
                start_response('200 OK', CORS_HEADERS + [('Content-Length', '0')])
                return [b'']
            else:
                response = client.get(full_path, headers=headers)

        # Build status line
        status = f"{response.status_code} {response.reason_phrase or 'OK'}"

        # Filter headers (exclude hop-by-hop headers)
        skip_headers = {'content-encoding', 'transfer-encoding', 'connection'}
        response_headers = [
            (k, v) for k, v in response.headers.items()
            if k.lower() not in skip_headers
        ]

        # Note: CORS headers are already added by FastAPI's CORSMiddleware
        # Don't add them again here to avoid duplicate headers

        start_response(status, response_headers)
        return [response.content]

    except Exception as e:
        import json
        import traceback
        error_detail = traceback.format_exc()
        print(f"WSGI Error: {error_detail}", flush=True)

        error_body = json.dumps({
            "error": str(e),
            "type": type(e).__name__,
            "detail": error_detail
        }).encode('utf-8')

        # Include CORS headers even on error responses
        start_response('500 Internal Server Error', [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(error_body))),
        ] + CORS_HEADERS)
        return [error_body]
