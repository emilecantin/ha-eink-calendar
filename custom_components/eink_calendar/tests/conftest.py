"""Test configuration — set up import paths for renderer tests."""

import sys
from pathlib import Path

# Add the eink_calendar directory so `from renderer.X import Y` works
_pkg_dir = Path(__file__).resolve().parent.parent
if str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))
