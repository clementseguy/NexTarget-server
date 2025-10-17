#!/usr/bin/env python
"""
Startup script for Render deployment.
Reads PORT from environment and starts uvicorn.
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    # Debug logs
    print(f"🔍 DEBUG: PORT env var = {os.environ.get('PORT', 'NOT SET')}", file=sys.stderr)
    print(f"🔍 DEBUG: Starting uvicorn on {host}:{port}", file=sys.stderr)
    print(f"🔍 DEBUG: All env vars: {list(os.environ.keys())}", file=sys.stderr)
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info"
    )

