#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environment
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Install Python dependencies for the backend
pip install -r "$CLAUDE_PROJECT_DIR/backend/requirements.txt"

# Install Playwright chromium browser
playwright install chromium
