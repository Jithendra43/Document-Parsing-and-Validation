#!/usr/bin/env python3
"""Run the FastAPI server."""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 