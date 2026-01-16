#!/usr/bin/env python
"""
Custom uvicorn runner that forces ProactorEventLoop on Windows.
This is needed because uvicorn's --reload mode uses SelectorEventLoop
which doesn't support subprocesses (required by Playwright).

Usage:
    python run.py                    # Development with reload
    python run.py --no-reload        # Production without reload
"""

import sys
import os

# Force ProactorEventLoop BEFORE anything else on Windows
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server


class ProactorServer(Server):
    """Custom uvicorn server that uses ProactorEventLoop on Windows."""

    def run(self, sockets=None):
        import asyncio
        if sys.platform == 'win32':
            # Force ProactorEventLoop for subprocess support
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
        return asyncio.run(self.serve(sockets=sockets))


if __name__ == "__main__":
    # Parse command line arguments
    reload = "--no-reload" not in sys.argv
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8081"))

    print(f"🚀 Starting E-Leiloes API on {host}:{port}")
    print(f"   Reload: {reload}")
    if sys.platform == 'win32':
        print("   Windows: Using ProactorEventLoop for Playwright support")

    config = Config(
        app="main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

    if sys.platform == 'win32':
        # Use custom server with ProactorEventLoop
        server = ProactorServer(config=config)
        server.run()
    else:
        # Linux/Mac: use standard uvicorn
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
