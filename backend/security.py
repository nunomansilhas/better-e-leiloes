"""
Security Module - API Protection
- HMAC Signature verification
- Rate Limiting with IP whitelist
"""

import os
import hmac
import hashlib
import time
from typing import Optional, Dict, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException
from functools import wraps

# ============== Configuration ==============

# SECURITY: API_SECRET_KEY must be configured in .env
# No default value to prevent accidental deployment with insecure key
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

# Check if running in production (not localhost)
_is_development = os.getenv("ENVIRONMENT", "development").lower() in ("development", "dev", "local")

if not API_SECRET_KEY:
    if _is_development:
        # Allow development without key (with warning)
        API_SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"
        print("⚠️  WARNING: API_SECRET_KEY not set. Using insecure dev key. Set in .env for production!")
    else:
        raise ValueError(
            "SECURITY ERROR: API_SECRET_KEY not configured!\n"
            "Set API_SECRET_KEY in .env file for production deployment.\n"
            "This is required to secure admin API endpoints."
        )

# Rate limiting config
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))  # requests per window
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# Whitelist IPs (no rate limit, no auth required for internal)
WHITELIST_IPS = {
    "127.0.0.1",
    "localhost",
    "::1",  # IPv6 localhost
    "0.0.0.0",
}

# Add custom whitelist from env
custom_whitelist = os.getenv("WHITELIST_IPS", "")
if custom_whitelist:
    WHITELIST_IPS.update(ip.strip() for ip in custom_whitelist.split(","))

# Signature timestamp tolerance (seconds)
SIGNATURE_TOLERANCE = 300  # 5 minutes


# ============== Rate Limiting ==============

class RateLimiter:
    """Simple in-memory rate limiter per IP"""

    def __init__(self):
        # {ip: [(timestamp, count), ...]}
        self._requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, ip: str) -> Tuple[bool, int]:
        """
        Check if IP is allowed to make a request.
        Returns (allowed, remaining_requests)
        """
        # Whitelist check
        if ip in WHITELIST_IPS:
            return True, -1  # -1 means unlimited

        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        # Clean old entries
        self._requests[ip] = [
            ts for ts in self._requests[ip]
            if ts > window_start
        ]

        # Check limit
        current_count = len(self._requests[ip])
        if current_count >= RATE_LIMIT_REQUESTS:
            return False, 0

        # Record this request
        self._requests[ip].append(now)

        remaining = RATE_LIMIT_REQUESTS - current_count - 1
        return True, remaining

    def get_stats(self) -> Dict:
        """Get rate limiter stats"""
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        active_ips = 0
        total_requests = 0

        for ip, timestamps in self._requests.items():
            recent = [ts for ts in timestamps if ts > window_start]
            if recent:
                active_ips += 1
                total_requests += len(recent)

        return {
            "active_ips": active_ips,
            "total_requests_in_window": total_requests,
            "window_seconds": RATE_LIMIT_WINDOW,
            "limit_per_ip": RATE_LIMIT_REQUESTS
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============== HMAC Signature ==============

def generate_signature(timestamp: str, method: str, path: str, body: str = "") -> str:
    """
    Generate HMAC-SHA256 signature.

    Client must generate the same signature:
    signature = HMAC-SHA256(secret, timestamp + method + path + body)
    """
    message = f"{timestamp}{method.upper()}{path}{body}"
    signature = hmac.new(
        API_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_signature(
    signature: str,
    timestamp: str,
    method: str,
    path: str,
    body: str = ""
) -> Tuple[bool, str]:
    """
    Verify HMAC signature.
    Returns (valid, error_message)
    """
    # Check timestamp is recent
    try:
        ts = int(timestamp)
        now = int(time.time())
        if abs(now - ts) > SIGNATURE_TOLERANCE:
            return False, f"Timestamp expired (tolerance: {SIGNATURE_TOLERANCE}s)"
    except ValueError:
        return False, "Invalid timestamp format"

    # Generate expected signature
    expected = generate_signature(timestamp, method, path, body)

    # Constant-time comparison to prevent timing attacks
    if hmac.compare_digest(signature, expected):
        return True, ""

    return False, "Invalid signature"


# ============== Helper Functions ==============

def get_client_ip(request: Request) -> str:
    """Get real client IP, handling proxies"""
    # Check X-Forwarded-For header (from reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the list is the original client
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def is_protected_endpoint(method: str, path: str) -> bool:
    """
    Determine if an endpoint requires authentication.
    - GET requests: generally open (read-only)
    - POST/PUT/DELETE: protected (mutations)
    """
    # Always open endpoints (even POST)
    open_endpoints = {
        "/api/sse",  # SSE connection
        "/api/logs/stream",  # Log streaming
        "/docs",
        "/openapi.json",
        "/",
    }

    if path in open_endpoints:
        return False

    # GET requests are generally open
    if method.upper() == "GET":
        return False

    # All other methods (POST, PUT, DELETE, PATCH) are protected
    return True


# ============== FastAPI Middleware ==============

async def security_middleware(request: Request, call_next):
    """
    Security middleware that handles:
    1. Rate limiting
    2. HMAC signature verification for protected endpoints
    """
    client_ip = get_client_ip(request)
    method = request.method
    path = request.url.path

    # --- Rate Limiting ---
    allowed, remaining = rate_limiter.is_allowed(client_ip)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
        )

    # Add rate limit headers to response
    response = None

    # --- HMAC Signature Verification ---
    if is_protected_endpoint(method, path):
        # Skip auth for whitelisted IPs (internal requests)
        if client_ip not in WHITELIST_IPS:
            signature = request.headers.get("X-Signature")
            timestamp = request.headers.get("X-Timestamp")

            if not signature or not timestamp:
                raise HTTPException(
                    status_code=401,
                    detail="Missing authentication headers (X-Signature, X-Timestamp)"
                )

            # Get request body for signature verification
            body = ""
            if method.upper() in ["POST", "PUT", "PATCH"]:
                body_bytes = await request.body()
                body = body_bytes.decode() if body_bytes else ""
                # Reset body for downstream handlers
                # Note: We need to recreate the receive function
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive

            valid, error = verify_signature(signature, timestamp, method, path, body)

            if not valid:
                raise HTTPException(
                    status_code=401,
                    detail=f"Authentication failed: {error}"
                )

    # Process request
    response = await call_next(request)

    # Add rate limit headers
    if remaining >= 0:
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(RATE_LIMIT_WINDOW)

    return response


# ============== JavaScript Helper Generator ==============

def get_frontend_auth_script() -> str:
    """
    Generate JavaScript code for frontend HMAC authentication.
    This should be injected into the frontend or served as a separate file.
    """
    return '''
// Security: HMAC Authentication Helper
// This generates signatures for protected API endpoints

const API_AUTH = {
    // This key should be set from environment/config
    // In production, consider fetching a session-specific key
    secretKey: null,

    setKey(key) {
        this.secretKey = key;
    },

    async generateSignature(method, path, body = '') {
        if (!this.secretKey) {
            console.warn('API_AUTH: Secret key not set');
            return null;
        }

        const timestamp = Math.floor(Date.now() / 1000).toString();
        const message = timestamp + method.toUpperCase() + path + body;

        // Use Web Crypto API for HMAC-SHA256
        const encoder = new TextEncoder();
        const keyData = encoder.encode(this.secretKey);
        const messageData = encoder.encode(message);

        const cryptoKey = await crypto.subtle.importKey(
            'raw',
            keyData,
            { name: 'HMAC', hash: 'SHA-256' },
            false,
            ['sign']
        );

        const signature = await crypto.subtle.sign(
            'HMAC',
            cryptoKey,
            messageData
        );

        // Convert to hex
        const hashArray = Array.from(new Uint8Array(signature));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

        return { signature: hashHex, timestamp };
    },

    async fetch(url, options = {}) {
        const method = options.method || 'GET';
        const path = new URL(url, window.location.origin).pathname;
        const body = options.body || '';

        // Only add auth for non-GET requests
        if (method.toUpperCase() !== 'GET' && this.secretKey) {
            const auth = await this.generateSignature(method, path, body);
            if (auth) {
                options.headers = {
                    ...options.headers,
                    'X-Signature': auth.signature,
                    'X-Timestamp': auth.timestamp
                };
            }
        }

        return fetch(url, options);
    }
};

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API_AUTH;
}
'''
