"""Interpretation of ESP32 boot diagnostics.

The ESP32 reports its reset reason and how far the previous boot progressed on
every check-in (see ``diagnostics.h`` in the firmware). This module turns those
raw signals into a plain-language explanation, so a reboot loop can be diagnosed
from the Home Assistant UI instead of a serial cable.

Kept free of Home Assistant imports so it can be unit-tested in isolation.
"""

from __future__ import annotations

# Stage names reported by the firmware, in the order a healthy boot passes
# through them. Must match BootStage / diag_stage_name() in diagnostics.h.
BOOT_STAGES = [
    "boot",
    "wifi_connected",
    "announced",
    "checked",
    "downloaded",
    "display_init",
    "display_sent",
    "display_refreshed",
    "sleeping",
]

# What the device was doing when it reached each stage, phrased so it can be
# dropped into "the device reset while ...".
_STAGE_ACTIVITY = {
    "boot": "starting up",
    "wifi_connected": "talking to Home Assistant",
    "announced": "checking for calendar changes",
    "checked": "downloading bitmap chunks",
    "downloaded": "initialising the display",
    "display_init": "sending bitmap data to the display",
    "display_sent": "running the 37-second display refresh",
    "display_refreshed": "finishing up after a successful refresh",
    "sleeping": "in deep sleep",
}

# Resets that mean something went wrong, mapped to the underlying cause.
_FAULT_RESETS = {
    "brownout": (
        "the supply voltage collapsed — the power source likely cannot sustain "
        "the current draw"
    ),
    "panic": "the firmware crashed",
    "task_wdt": "the task watchdog fired — something blocked for over 120s",
    "int_wdt": "the interrupt watchdog fired — something blocked with interrupts off",
    "other_wdt": "a watchdog fired",
}


def stage_index(stage: str | None) -> int:
    """Position of a stage in the boot sequence, or -1 if unrecognised."""
    if stage in BOOT_STAGES:
        return BOOT_STAGES.index(stage)
    return -1


# How many consecutive mismatched check-ins before we call a fingerprint stuck.
STUCK_FINGERPRINT_THRESHOLD = 3


def is_fingerprint_stuck(checkin_log: list[dict]) -> bool:
    """Detect a device repeatedly presenting the same outdated fingerprint.

    The device only persists a new ETag after a completed display refresh, so
    if it keeps sending an identical ETag that never matches the server's, the
    refresh is not completing and the same image is re-downloaded every cycle.

    Entries lacking a recorded outcome (older firmware, or a check that errored
    before the render) are skipped rather than treated as matches.
    """
    scored = [
        entry
        for entry in checkin_log
        if "etag_match" in entry and entry.get("device_etag") is not None
    ]
    recent = scored[-STUCK_FINGERPRINT_THRESHOLD:]
    if len(recent) < STUCK_FINGERPRINT_THRESHOLD:
        return False
    if any(entry["etag_match"] for entry in recent):
        return False
    return len({entry["device_etag"] for entry in recent}) == 1


def diagnose(
    *,
    reset_reason: str | None = None,
    last_stage: str | None = None,
    is_rapid: bool = False,
    last_error: str | None = None,
    median_interval: float | None = None,
    expected_interval: float | None = None,
    fingerprint_stuck: bool = False,
    device_etag: str | None = None,
    server_etag: str | None = None,
    display_valid: bool | None = None,
) -> str:
    """Explain why the device is behaving the way it is.

    Returns a single sentence suitable for display as a sensor attribute.
    """
    activity = _STAGE_ACTIVITY.get(last_stage or "", "at an unknown point")
    stage_label = last_stage or "unknown"

    fingerprints = ""
    if fingerprint_stuck:
        never = (
            " It has never completed a refresh."
            if display_valid is False
            else ""
        )
        fingerprints = (
            f" It keeps presenting the same fingerprint ({device_etag}) while the "
            f"server is serving {server_etag}, so the new one is never being "
            f"stored.{never}"
        )

    # A fault reset is the strongest signal we have — report it regardless of
    # whether the check-in cadence has drifted far enough to look "rapid" yet.
    if reset_reason in _FAULT_RESETS:
        return (
            f"Device reset with reason '{reset_reason}' while {activity} "
            f"(reached stage '{stage_label}'): {_FAULT_RESETS[reset_reason]}."
            f"{fingerprints}"
        )

    if not is_rapid:
        if fingerprint_stuck:
            return (
                "Device is checking in on schedule but the display is not "
                f"updating.{fingerprints}"
            )
        if last_error:
            return (
                "Device is checking in on schedule, but the last cycle reported "
                f"an error: {last_error}."
            )
        return "Device is checking in on schedule."

    # Rapid, but every reset was a clean deep-sleep wake: the firmware is
    # deliberately taking one of its short-sleep retry paths.
    cadence = ""
    if median_interval is not None and expected_interval is not None:
        cadence = (
            f" Checking in every ~{round(median_interval)}s versus an expected "
            f"{round(expected_interval)}s."
        )

    if last_error:
        return (
            f"Device is rebooting cleanly into the retry path after reaching "
            f"stage '{stage_label}'. Last reported error: {last_error}."
            f"{fingerprints}{cadence}"
        )

    idx = stage_index(last_stage)
    if 0 <= idx < stage_index("display_refreshed"):
        return (
            f"Device is rebooting cleanly but only reaching stage '{stage_label}' "
            f"(it was {activity}) — the display refresh is not completing, so the "
            f"ETag is never saved and the calendar is re-downloaded every cycle."
            f"{fingerprints}{cadence}"
        )

    return (
        f"Device is checking in rapidly after reaching stage '{stage_label}' "
        f"with no error reported.{fingerprints}{cadence}"
    )
