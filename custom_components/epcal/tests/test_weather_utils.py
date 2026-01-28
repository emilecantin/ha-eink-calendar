"""Unit tests for weather_utils module."""

import unittest
from datetime import datetime

from ..renderer.weather_utils import get_forecast_for_date, get_weather_icon


class TestGetWeatherIcon(unittest.TestCase):
    """Test get_weather_icon function."""

    def test_known_conditions(self):
        """Test known weather conditions map to correct icons."""
        test_cases = {
            "sunny": "☀",
            "clear": "☀",
            "clear-night": "☽",
            "partlycloudy": "⛅",
            "cloudy": "☁",
            "rainy": "☂",
            "snowy": "❄",
            "lightning": "⚡",
        }

        for condition, expected_icon in test_cases.items():
            with self.subTest(condition=condition):
                result = get_weather_icon(condition)
                self.assertEqual(result, expected_icon)

    def test_case_insensitive(self):
        """Test that weather conditions are case-insensitive."""
        self.assertEqual(get_weather_icon("SUNNY"), "☀")
        self.assertEqual(get_weather_icon("Sunny"), "☀")
        self.assertEqual(get_weather_icon("sunny"), "☀")

    def test_unknown_condition(self):
        """Test unknown condition returns question mark."""
        result = get_weather_icon("unknown_condition")
        self.assertEqual(result, "?")

    def test_empty_condition(self):
        """Test empty condition returns question mark."""
        result = get_weather_icon("")
        self.assertEqual(result, "?")


class TestGetForecastForDate(unittest.TestCase):
    """Test get_forecast_for_date function."""

    def setUp(self):
        """Set up test fixtures."""
        self.weather_data = {
            "condition": "sunny",
            "temperature": 20,
            "forecast": [
                {
                    "datetime": "2026-01-26T00:00:00",
                    "condition": "sunny",
                    "temperature": 22,
                    "templow": 15,
                },
                {
                    "datetime": "2026-01-27T00:00:00",
                    "condition": "cloudy",
                    "temperature": 18,
                    "templow": 12,
                },
                {
                    "datetime": "2026-01-28T00:00:00",
                    "condition": "rainy",
                    "temperature": 16,
                    "templow": 10,
                },
            ],
        }

    def test_forecast_for_existing_date(self):
        """Test getting forecast for a date that exists."""
        target_date = datetime(2026, 1, 27, 14, 30)

        result = get_forecast_for_date(self.weather_data, target_date)  # type: ignore[arg-type]

        self.assertIsNotNone(result)
        assert result is not None  # Type narrowing for pyright
        self.assertEqual(result["condition"], "cloudy")
        self.assertEqual(result["temperature"], 18)
        self.assertEqual(result["templow"], 12)

    def test_forecast_for_first_date(self):
        """Test getting forecast for the first date."""
        target_date = datetime(2026, 1, 26, 10, 0)

        result = get_forecast_for_date(self.weather_data, target_date)  # type: ignore[arg-type]

        self.assertIsNotNone(result)
        assert result is not None  # Type narrowing for pyright
        self.assertEqual(result["condition"], "sunny")

    def test_forecast_for_last_date(self):
        """Test getting forecast for the last date."""
        target_date = datetime(2026, 1, 28, 10, 0)

        result = get_forecast_for_date(self.weather_data, target_date)  # type: ignore[arg-type]

        self.assertIsNotNone(result)
        assert result is not None  # Type narrowing for pyright
        self.assertEqual(result["condition"], "rainy")

    def test_forecast_for_nonexistent_date(self):
        """Test getting forecast for a date that doesn't exist."""
        target_date = datetime(2026, 1, 30, 10, 0)

        result = get_forecast_for_date(self.weather_data, target_date)  # type: ignore[arg-type]

        self.assertIsNone(result)

    def test_none_weather_data(self):
        """Test with None weather data."""
        target_date = datetime(2026, 1, 27, 10, 0)

        result = get_forecast_for_date(None, target_date)  # type: ignore[arg-type]

        self.assertIsNone(result)

    def test_weather_data_without_forecast(self):
        """Test with weather data that doesn't have forecast key."""
        weather_data = {"condition": "sunny", "temperature": 20}
        target_date = datetime(2026, 1, 27, 10, 0)

        result = get_forecast_for_date(weather_data, target_date)  # type: ignore[arg-type]

        self.assertIsNone(result)

    def test_forecast_with_time_component(self):
        """Test that time component is ignored when matching dates."""
        target_date = datetime(2026, 1, 27, 23, 59, 59)

        result = get_forecast_for_date(self.weather_data, target_date)  # type: ignore[arg-type]

        self.assertIsNotNone(result)
        assert result is not None  # Type narrowing for pyright
        self.assertEqual(result["condition"], "cloudy")


if __name__ == "__main__":
    unittest.main()
