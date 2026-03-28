#!/usr/bin/env python3
"""Provision a fresh Home Assistant instance for integration testing.

Handles onboarding (creating first user) and obtaining an access token.
Idempotent: if HA is already onboarded with our test credentials, it logs
in. If onboarded with unknown credentials, it prints an error suggesting
to reset the test environment.

Prints the access token to stdout on success. All diagnostic output goes
to stderr so callers can capture just the token via:

    TOKEN=$(python3 provision_ha.py)

Usage:
    export HA_URL=http://localhost:18123
    TOKEN=$(python3 provision_ha.py)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HA_URL = os.environ.get("HA_URL", "http://localhost:18123")

# Test user credentials — only used inside the ephemeral test container
TEST_USER = "test"
TEST_PASSWORD = "testpassword123"
TEST_LANGUAGE = "en"

CLIENT_ID = f"{HA_URL}/"


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _post_json(url: str, data: dict) -> dict:
    """POST JSON and return the parsed response."""
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _post_form(url: str, data: dict) -> dict:
    """POST form-encoded data and return parsed JSON."""
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _get(url: str) -> list | dict:
    """GET and return parsed JSON response."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _needs_onboarding() -> bool:
    """Check if HA still needs onboarding."""
    try:
        steps = _get(f"{HA_URL}/api/onboarding")
        return any(
            step.get("step") == "user" and not step.get("done") for step in steps
        )
    except Exception as exc:
        _log(f"Could not check onboarding status: {exc}")
        return True


def _exchange_code(auth_code: str) -> str:
    """Exchange an authorization code for an access token."""
    tokens = _post_form(
        f"{HA_URL}/auth/token",
        {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": CLIENT_ID,
        },
    )
    access_token = tokens.get("access_token")
    if not access_token:
        raise RuntimeError(f"Token exchange failed: {tokens}")
    return access_token


def _post_json_auth(url: str, data: dict, token: str) -> dict:
    """POST JSON with Bearer auth and return the parsed response."""
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _do_onboarding() -> str:
    """Complete the HA onboarding flow and return an access token."""
    _log("Creating test user via onboarding...")
    result = _post_json(
        f"{HA_URL}/api/onboarding/users",
        {
            "client_id": CLIENT_ID,
            "name": TEST_USER,
            "username": TEST_USER,
            "password": TEST_PASSWORD,
            "language": TEST_LANGUAGE,
        },
    )
    auth_code = result.get("auth_code")
    if not auth_code:
        raise RuntimeError(f"Onboarding did not return an auth_code: {result}")

    _log("Exchanging auth code for access token...")
    token = _exchange_code(auth_code)

    # Complete remaining onboarding steps (best-effort, order matters)
    # These require auth, so use the token we just obtained.
    for step in ("core_config", "analytics", "integration"):
        try:
            _post_json_auth(f"{HA_URL}/api/onboarding/{step}", {}, token)
            _log(f"  Completed onboarding step: {step}")
        except Exception as exc:
            _log(f"  Onboarding step '{step}' skipped: {exc}")

    return token


def _login() -> str:
    """Log in with test user credentials and return an access token."""
    _log("Logging in with test credentials...")

    # Step 1: Start a login flow
    result = _post_json(
        f"{HA_URL}/auth/login_flow",
        {
            "client_id": CLIENT_ID,
            "handler": ["homeassistant", None],
            "redirect_uri": f"{HA_URL}/?auth_callback=1",
        },
    )
    flow_id = result["flow_id"]

    # Step 2: Submit credentials
    try:
        result = _post_json(
            f"{HA_URL}/auth/login_flow/{flow_id}",
            {
                "client_id": CLIENT_ID,
                "username": TEST_USER,
                "password": TEST_PASSWORD,
            },
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 400:
            raise RuntimeError(
                "Login failed — HA was onboarded with different credentials.\n"
                "Run: make ha-test-clean ha-test-up\n"
                "to reset the test environment."
            ) from exc
        raise

    auth_code = result.get("result")
    if not auth_code:
        raise RuntimeError(
            f"Login flow did not return a code: {result}\n"
            "This may mean HA was onboarded with different credentials.\n"
            "Run: make ha-test-clean ha-test-up"
        )

    _log("Exchanging auth code for access token...")
    return _exchange_code(auth_code)


def main() -> int:
    try:
        if _needs_onboarding():
            _log("HA needs onboarding — provisioning test user...")
            token = _do_onboarding()
        else:
            _log("HA already onboarded — logging in...")
            token = _login()
    except Exception as exc:
        _log(f"ERROR: {exc}")
        return 1

    # Print ONLY the token to stdout
    print(token)
    _log("Access token obtained successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
