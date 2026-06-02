"""
Streamlit entrypoint for Hugging Face Spaces.

The real frontend lives in career_agent/frontend/app.py. This wrapper keeps
Spaces from falling back to an older root-level app and ensures imports resolve
from the project package directory.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent / "career_agent"
FRONTEND_APP = PROJECT_ROOT / "frontend" / "app.py"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

runpy.run_path(str(FRONTEND_APP), run_name="__main__")
