"""Locale-independent date formatting for supported languages."""

from datetime import datetime

_TRANSLATIONS: dict[str, dict[str, list[str]]] = {
    "fr": {
        "day_names": [
            "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
        ],
        "day_abbrs": ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"],
        "month_names": [
            "", "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre",
        ],
        "month_abbrs": [
            "", "JAN", "FÉV", "MAR", "AVR", "MAI", "JUN",
            "JUL", "AOÛ", "SEP", "OCT", "NOV", "DÉC",
        ],
    },
    "en": {
        "day_names": [
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        ],
        "day_abbrs": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
        "month_names": [
            "", "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ],
        "month_abbrs": [
            "", "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
            "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
        ],
    },
}

DEFAULT_LANG = "fr"


def _get(lang: str, key: str) -> list[str]:
    return _TRANSLATIONS.get(lang, _TRANSLATIONS[DEFAULT_LANG])[key]


def format_day_name(dt: datetime, lang: str = DEFAULT_LANG) -> str:
    """Full day name, e.g. 'Lundi' / 'Monday'."""
    return _get(lang, "day_names")[dt.weekday()].capitalize()


def format_day_abbr(dt: datetime, lang: str = DEFAULT_LANG) -> str:
    """3-letter uppercase day abbreviation, e.g. 'LUN' / 'MON'."""
    return _get(lang, "day_abbrs")[dt.weekday()]


def format_month_abbr(dt: datetime, lang: str = DEFAULT_LANG) -> str:
    """3-letter uppercase month abbreviation, e.g. 'JAN'."""
    return _get(lang, "month_abbrs")[dt.month]


def format_date(dt: datetime, lang: str = DEFAULT_LANG) -> str:
    """Full date string, e.g. '26 janvier 2026' / 'January 26, 2026'."""
    month = _get(lang, "month_names")[dt.month]
    if lang == "en":
        return f"{month.capitalize()} {dt.day}, {dt.year}"
    return f"{dt.day} {month} {dt.year}"
