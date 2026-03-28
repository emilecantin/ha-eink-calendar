"""Tests for coordinator encapsulation and callback lifecycle (Unit 5)."""

from unittest.mock import MagicMock

from custom_components.eink_calendar.const import (
    CONF_DEVICE_NAME,
    CONF_MAC_ADDRESS,
    DOMAIN,
)
from custom_components.eink_calendar.coordinator import EinkCalendarDataCoordinator


def make_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {}}
    return hass


def make_entry(entry_id="test-entry-1", mac="AA:BB:CC:DD:EE:FF", name="Kitchen Calendar"):
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = {CONF_MAC_ADDRESS: mac, CONF_DEVICE_NAME: name}
    entry.options = {}
    return entry


def make_coordinator(hass=None, entry=None):
    hass = hass or make_hass()
    entry = entry or make_entry()
    return EinkCalendarDataCoordinator(hass, entry)


class TestOnCheckinReturnsRemovalCallable:
    def test_on_checkin_returns_callable(self):
        """on_checkin() should return a callable for removal."""
        coord = make_coordinator()
        cb = MagicMock()
        remove = coord.on_checkin(cb)
        assert callable(remove)

    def test_removal_callable_prevents_future_calls(self):
        """After calling the removal callable, the callback should not fire."""
        coord = make_coordinator()
        cb = MagicMock()
        remove = coord.on_checkin(cb)

        # Callback fires before removal
        coord.record_checkin()
        assert cb.call_count == 1

        # Remove and verify it no longer fires
        remove()
        coord.record_checkin()
        assert cb.call_count == 1  # Still 1, not 2

    def test_removal_is_idempotent(self):
        """Calling remove() multiple times should not raise."""
        coord = make_coordinator()
        cb = MagicMock()
        remove = coord.on_checkin(cb)
        remove()
        remove()  # Should not raise


class TestDuplicateCallbackRegistration:
    def test_same_callback_registered_twice_only_called_once(self):
        """Registering the same callback twice should only call it once (set behavior)."""
        coord = make_coordinator()
        cb = MagicMock()
        coord.on_checkin(cb)
        coord.on_checkin(cb)
        coord.record_checkin()
        cb.assert_called_once()


class TestConsumeForceRefresh:
    def test_returns_false_by_default(self):
        """consume_force_refresh() should return False when no force refresh pending."""
        coord = make_coordinator()
        assert coord.consume_force_refresh() is False

    def test_returns_true_after_force_refresh(self):
        """consume_force_refresh() should return True after force_refresh() is called."""
        coord = make_coordinator()
        coord.force_refresh()
        assert coord.consume_force_refresh() is True

    def test_returns_false_on_second_call(self):
        """consume_force_refresh() should return False on second consecutive call."""
        coord = make_coordinator()
        coord.force_refresh()
        assert coord.consume_force_refresh() is True
        assert coord.consume_force_refresh() is False


class TestRecordDeviceErrorFiresCallbacks:
    def test_record_device_error_fires_checkin_callbacks(self):
        """record_device_error() should fire checkin callbacks so sensors update."""
        coord = make_coordinator()
        cb = MagicMock()
        coord.on_checkin(cb)
        coord.record_device_error("display timeout")
        cb.assert_called_once()

    def test_record_device_error_fires_callbacks_each_time(self):
        """Each call to record_device_error() should fire callbacks."""
        coord = make_coordinator()
        cb = MagicMock()
        coord.on_checkin(cb)
        coord.record_device_error("error1")
        coord.record_device_error("error2")
        assert cb.call_count == 2
