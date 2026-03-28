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
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.entity_registry",
    "homeassistant.helpers.event",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.components.sensor",
    "homeassistant.util",
    "homeassistant.util.dt",
    "aiohttp",
    "aiohttp.web",
    "voluptuous",
]
for mod in _HA_MODULES:
    sys.modules.setdefault(mod, MagicMock())


# Provide real base classes so our code can inherit properly.
# HA's _attr_* pattern: setting _attr_foo makes self.foo return that value.
class _FakeEntity:
    """Minimal Entity base that supports HA's _attr_* property pattern."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @property
    def name(self):
        return getattr(self, "_attr_name", None)

    @property
    def unique_id(self):
        return getattr(self, "_attr_unique_id", None)

    @property
    def icon(self):
        return getattr(self, "_attr_icon", None)

    @property
    def device_class(self):
        return getattr(self, "_attr_device_class", None)

    @property
    def device_info(self):
        return getattr(self, "_attr_device_info", None)


class _FakeSensorEntity(_FakeEntity):
    """Minimal SensorEntity stand-in."""

    @property
    def native_value(self):
        return getattr(self, "_attr_native_value", None)


class _FakeDataUpdateCoordinator:
    """Minimal DataUpdateCoordinator stand-in."""

    def __init__(self, hass, logger, *, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None
        self.last_update_success = True
        self._listeners = []

    def async_set_updated_data(self, data):
        self.data = data
        for callback in self._listeners:
            callback()

    def async_add_listener(self, callback):
        self._listeners.append(callback)
        return lambda: self._listeners.remove(callback)

    async def async_request_refresh(self):
        pass


# Make dt_util.now() return real datetimes (not MagicMock)
# Note: `from homeassistant.util import dt` resolves to sys.modules["homeassistant.util"].dt
# which is a MagicMock attribute, NOT sys.modules["homeassistant.util.dt"]
from datetime import datetime, timezone

_dt_mock = sys.modules["homeassistant.util"].dt
_dt_mock.now = lambda: datetime.now(timezone.utc)
_dt_mock.start_of_local_day = lambda: datetime.now(timezone.utc).replace(
    hour=0, minute=0, second=0, microsecond=0
)

# Patch the real base classes into the mocked modules
sys.modules["homeassistant.components.sensor"].SensorEntity = _FakeSensorEntity
sys.modules["homeassistant.components.sensor"].SensorDeviceClass = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = (
    _FakeDataUpdateCoordinator
)
class _FakeUpdateFailed(Exception):
    """Stand-in for homeassistant.helpers.update_coordinator.UpdateFailed."""


sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = _FakeUpdateFailed
