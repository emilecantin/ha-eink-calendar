"""Type definitions for E-Ink Calendar renderer."""

from datetime import datetime
from typing import TypedDict

from PIL import ImageFont


class CalendarEvent(TypedDict, total=False):
    """Calendar event dictionary.

    Uses total=False because events are built incrementally in _process_events
    and not all fields are present on raw HA events vs processed events.
    """

    id: str
    title: str
    start: datetime
    end: datetime
    allDay: bool
    calendarId: str
    calendarIcon: str
    calendarName: str


class WeatherForecast(TypedDict):
    """Weather forecast dictionary."""

    condition: str
    temperature: float
    templow: float
    datetime: str


class WeatherData(TypedDict):
    """Weather data dictionary."""

    condition: str
    temperature: float
    forecast: list[WeatherForecast]


class FontDict(TypedDict):
    """Font dictionary with size variants."""

    regular: dict[int, ImageFont.FreeTypeFont]
    medium: dict[int, ImageFont.FreeTypeFont]
    bold: dict[int, ImageFont.FreeTypeFont]


class RenderOptions(TypedDict, total=False):
    """Rendering options dictionary.

    All fields are optional, so total=False is correct here.
    """

    language: str
    font_regular: str | None
    font_medium: str | None
    font_bold: str | None
    waste_calendars: list[str]
    legend_items: list[dict[str, str]]
