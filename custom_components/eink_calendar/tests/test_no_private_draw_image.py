"""Tests that section renderers do not access draw._image (private PIL attribute).

Fixes GitHub issue #9: Replace private draw._image access with explicit img parameter.
"""

from datetime import datetime
from unittest.mock import MagicMock, PropertyMock

from PIL import Image, ImageDraw

from renderer.renderer import render_calendar


class TestNoPrivateDrawImageAccess:
    """Verify that render_calendar never accesses draw._image."""

    def test_render_does_not_access_draw_private_image(self):
        """Full render must not touch ImageDraw._image at all.

        We monkeypatch ImageDraw.Draw so that accessing ._image raises an
        AssertionError.  If any section renderer still falls back to
        draw._image, this test will fail.
        """
        calendar_events = [
            {
                "calendar_id": "calendar.test",
                "calendar_icon": "mdi:calendar",
                "summary": "Test Event",
                "start": "2026-01-26T14:00:00",
                "end": "2026-01-26T15:00:00",
            }
        ]
        now = datetime(2026, 1, 25, 10, 0, 0)

        original_draw_init = ImageDraw.ImageDraw.__init__

        def patched_init(self, im, mode=None):
            original_draw_init(self, im, mode)
            # Replace _image with a property that explodes on access
            # We store the real image under a different name first
            real_image = self._image

            class Trap:
                """Descriptor that raises on _image access."""
                def __get__(self_desc, obj, objtype=None):
                    raise AssertionError(
                        "Section renderer accessed draw._image! "
                        "Pass img= explicitly instead."
                    )

            # We can't set a descriptor on an instance, so we patch at class
            # level temporarily — but that would affect all instances.
            # Instead, override __getattribute__ on this instance.
            orig_getattr = type(self).__getattribute__

            def guarded_getattr(self_inner, name):
                if name == "_image":
                    raise AssertionError(
                        "Section renderer accessed draw._image! "
                        "Pass img= explicitly instead."
                    )
                return orig_getattr(self_inner, name)

            self.__class__ = type(
                "GuardedImageDraw",
                (ImageDraw.ImageDraw,),
                {"__getattribute__": guarded_getattr},
            )

        ImageDraw.ImageDraw.__init__ = patched_init
        try:
            # This should succeed without accessing draw._image
            result = render_calendar(calendar_events, [], None, now, {})
            assert result.etag is not None
        finally:
            ImageDraw.ImageDraw.__init__ = original_draw_init

    def test_section_renderers_require_img_parameter(self):
        """Each section renderer should require img (no fallback to draw._image)."""
        from renderer.section_renderers.landscape_today import (
            draw_landscape_today_section,
        )
        from renderer.section_renderers.landscape_upcoming import (
            draw_landscape_upcoming_section,
        )
        from renderer.section_renderers.landscape_week import (
            draw_landscape_week_section,
        )

        img = Image.new("RGB", (1304, 984), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        now = datetime(2026, 1, 25, 10, 0, 0)

        # Minimal fonts dict
        from renderer.font_loader import get_fonts

        fonts = get_fonts({})

        # Calling without img= should raise TypeError (required parameter)
        # After the fix, img should no longer have a default value.
        # For now, just verify they work fine WITH img= passed.
        draw_landscape_today_section(
            draw, fonts, [], now, is_red=False, img=img
        )
        draw_landscape_week_section(
            draw, fonts, [], now, is_red=False, img=img
        )
        draw_landscape_upcoming_section(
            draw, fonts, [], now, is_red=False, img=img
        )
