"""Tests for constant import paths (regression for #46).

MDI_TO_UNICODE must be importable from renderer.const (no HA dependencies),
NOT from the integration-level const module.
"""


def test_mdi_to_unicode_importable_from_renderer_const():
    """MDI_TO_UNICODE should be in the renderer sub-package."""
    from renderer.const import MDI_TO_UNICODE

    assert isinstance(MDI_TO_UNICODE, dict)
    assert len(MDI_TO_UNICODE) > 0
    # Spot-check a known entry
    assert "mdi:calendar" in MDI_TO_UNICODE


def test_mdi_to_unicode_not_in_integration_const():
    """MDI_TO_UNICODE must NOT be in the top-level integration const module."""
    from custom_components.eink_calendar import const as integration_const

    assert not hasattr(integration_const, "MDI_TO_UNICODE")


def test_renderer_const_has_no_ha_dependencies():
    """renderer.const should import cleanly without Home Assistant."""
    import importlib
    import sys

    # Remove any cached import to force a fresh load
    mod_name = "renderer.const"
    saved = sys.modules.pop(mod_name, None)
    try:
        mod = importlib.import_module(mod_name)
        assert hasattr(mod, "MDI_TO_UNICODE")
    finally:
        if saved is not None:
            sys.modules[mod_name] = saved
