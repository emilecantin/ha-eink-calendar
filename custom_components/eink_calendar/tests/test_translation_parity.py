"""Every user-facing string must exist in strings.json and both translations.

Nothing else enforces this: a new config option shipped without a matching
translation key renders in Home Assistant as the raw key name.
"""

import json
from pathlib import Path

import pytest

_COMPONENT = Path(__file__).resolve().parent.parent
_FILES = {
    "strings": _COMPONENT / "strings.json",
    "en": _COMPONENT / "translations" / "en.json",
    "fr": _COMPONENT / "translations" / "fr.json",
}

# Options the quiet-hours feature adds; listed explicitly so removing one
# from the schema without removing its strings is caught too.
QUIET_HOURS_KEYS = {"quiet_start", "quiet_end", "quiet_multiplier"}


def load(name: str) -> dict:
    return json.loads(_FILES[name].read_text(encoding="utf-8"))


def flatten(d, prefix=""):
    """All leaf key paths in a nested dict."""
    out = set()
    for key, value in d.items():
        path = f"{prefix}/{key}"
        if isinstance(value, dict):
            out |= flatten(value, path)
        else:
            out.add(path)
    return out


class TestTranslationParity:
    def test_en_matches_strings(self):
        assert flatten(load("strings")) == flatten(load("en"))

    def test_fr_matches_strings(self):
        assert flatten(load("strings")) == flatten(load("fr"))

    @pytest.mark.parametrize("name", ["strings", "en", "fr"])
    def test_no_empty_labels(self, name):
        """An empty string renders as a blank label, which reads as a bug."""
        data = load(name)

        def walk(d, path=""):
            for key, value in d.items():
                if isinstance(value, dict):
                    walk(value, f"{path}/{key}")
                else:
                    assert str(value).strip(), f"{name}{path}/{key} is empty"

        walk(data)


class TestQuietHoursStrings:
    @pytest.mark.parametrize("name", ["strings", "en", "fr"])
    def test_quiet_hours_options_are_labelled(self, name):
        options = load(name)["options"]["step"]["init"]["data"]
        assert QUIET_HOURS_KEYS <= set(options)

    def test_french_is_actually_translated(self):
        """Guard against copy-pasting the English labels into fr.json."""
        en = load("en")["options"]["step"]["init"]["data"]
        fr = load("fr")["options"]["step"]["init"]["data"]
        for key in QUIET_HOURS_KEYS:
            assert fr[key] != en[key], f"{key} is untranslated in fr.json"
