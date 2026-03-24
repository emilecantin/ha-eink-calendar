"""Type definitions for E-Ink Calendar renderer."""

from datetime import datetime
from typing import TypedDict

from PIL import ImageFont


class CalendarEvent(TypedDict):
    """Calendar event dictionary."""

    title: str
    start: datetime
    end: datetime
    allDay: bool
    calendarId: str
    calendarIcon: str


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

    waste_calendars: list[str]  # Note: Using 'waste_calendars' to match actual usage
    legend_items: list[dict[str, str]]
