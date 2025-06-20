#!/usr/bin/env python3
"""Run the Streamlit frontend."""

import subprocess
import sys
from app.config import settings

if __name__ == "__main__":
    cmd = [
        sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
        "--server.port", str(settings.streamlit_port),
        "--server.address", settings.streamlit_host,
        "--server.headless", "true" if not settings.debug else "false"
    ]
    
    subprocess.run(cmd) 