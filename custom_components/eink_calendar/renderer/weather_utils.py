"""Weather utilities for E-Ink Calendar calendar rendering.

Handles weather condition icons and forecast lookups.
"""

from datetime import datetime

from PIL import Image

from .icon_utils import get_weather_icon as get_weather_icon_image
from .types import WeatherData, WeatherForecast


def get_weather_icon(condition: str) -> Image.Image | None:
    """Get weather icon PIL Image for a condition.

    Args:
        condition: Weather condition string (e.g., "sunny", "rainy")

    Returns:
        PIL Image object for the weather icon, or None if not found

    Note:
        This now returns a PIL Image instead of a Unicode symbol.
        Use img.paste(icon, (x, y), icon) to paste with transparency.
    """
    return get_weather_icon_image(condition.lower())


def get_forecast_for_date(
    weather_data: WeatherData | None, target_date: datetime
) -> WeatherForecast | None:
    """Get forecast for a specific date from weather data.

    Args:
        weather_data: Weather data from coordinator (includes forecast array)
        target_date: Date to find forecast for

    Returns:
        Forecast dict for the date, or None if not found
    """
    if not weather_data or "forecast" not in weather_data:
        return None

    forecasts = weather_data["forecast"]
    for forecast in forecasts:
        # Parse forecast datetime string
        forecast_date_str = forecast.get("datetime")
        if not forecast_date_str:
            continue

        # Parse the datetime (could be ISO string)
        from dateutil import parser

        forecast_date = parser.parse(forecast_date_str)

        # Compare dates
        if forecast_date.date() == target_date.date():
            return forecast

    return None
