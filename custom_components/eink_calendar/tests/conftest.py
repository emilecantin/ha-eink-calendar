"""Test configuration — set up import paths for renderer and integration tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add the eink_calendar directory so `from renderer.X import Y` works
_pkg_dir = Path(__file__).resolve().parent.parent
if str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))

# Add the repo root so `from custom_components.eink_calendar.X import Y` works
_repo_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Mock homeassistant and voluptuous so integration modules can be imported
# without a full HA installation
_HA_MODULES = [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.components.http",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_registry",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.util",
    "homeassistant.util.dt",
    "aiohttp",
    "aiohttp.web",
    "voluptuous",
]
for mod in _HA_MODULES:
    sys.modules.setdefault(mod, MagicMock())
