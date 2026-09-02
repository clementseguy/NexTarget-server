#!/usr/bin/env python
"""
Startup script for Render deployment.

Runs pending Alembic migrations (NT-071) before starting Uvicorn; startup is
aborted if migrations fail so a broken/partial schema never serves traffic.
Then reads PORT from environment and starts uvicorn.
"""
import os
import sys

import uvicorn

from scripts.run_migrations import run_migrations

if __name__ == "__main__":
    try:
        run_migrations()
    except Exception as exc:  # noqa: BLE001 - see scripts/run_migrations.py
        print(
            f"Database migration failed ({type(exc).__name__}); aborting startup.",
            file=sys.stderr,
        )
        sys.exit(1)

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

