"""Unit tests for weather_utils module."""

from datetime import datetime

from renderer.weather_utils import get_forecast_for_date


class TestGetForecastForDate:
    def test_forecast_for_existing_date(self):
        weather_data = {
            "condition": "sunny",
            "temperature": 20,
            "forecast": [
                {"datetime": "2026-01-26T00:00:00", "condition": "sunny", "temperature": 22, "templow": 15},
                {"datetime": "2026-01-27T00:00:00", "condition": "cloudy", "temperature": 18, "templow": 12},
                {"datetime": "2026-01-28T00:00:00", "condition": "rainy", "temperature": 16, "templow": 10},
            ],
        }
        result = get_forecast_for_date(weather_data, datetime(2026, 1, 27, 14, 30))
        assert result is not None
        assert result["condition"] == "cloudy"
        assert result["temperature"] == 18

    def test_forecast_for_nonexistent_date(self):
        weather_data = {
            "forecast": [
                {"datetime": "2026-01-27T00:00:00", "condition": "rainy"},
            ],
        }
        assert get_forecast_for_date(weather_data, datetime(2026, 1, 30)) is None

    def test_none_weather_data(self):
        assert get_forecast_for_date(None, datetime(2026, 1, 27)) is None

    def test_missing_forecast_key(self):
        assert get_forecast_for_date({"condition": "sunny"}, datetime(2026, 1, 27)) is None

    def test_empty_forecast(self):
        assert get_forecast_for_date({"forecast": []}, datetime(2026, 1, 27)) is None

    def test_forecast_without_datetime_skipped(self):
        weather_data = {
            "forecast": [
                {"condition": "sunny", "temperature": 14},
                {"datetime": "2026-01-26T08:00:00", "condition": "cloudy", "temperature": 10},
            ],
        }
        result = get_forecast_for_date(weather_data, datetime(2026, 1, 26))
        assert result is not None
        assert result["condition"] == "cloudy"

    def test_time_component_ignored(self):
        weather_data = {
            "forecast": [
                {"datetime": "2026-01-27T00:00:00", "condition": "cloudy", "temperature": 18},
            ],
        }
        result = get_forecast_for_date(weather_data, datetime(2026, 1, 27, 23, 59, 59))
        assert result is not None
        assert result["condition"] == "cloudy"

    def test_timezone_aware_forecast(self):
        weather_data = {
            "forecast": [
                {"datetime": "2026-01-26T08:00:00-05:00", "condition": "sunny", "temperature": 14},
            ],
        }
        result = get_forecast_for_date(weather_data, datetime(2026, 1, 26))
        assert result is not None
        assert result["condition"] == "sunny"
