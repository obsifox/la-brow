"""Shared test fixtures and repository path setup."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture()
def profile_payload() -> dict:
    return {
        "name": "berlin-test",
        "profile_version": 2,
        "geolocation_mode": "manual",
        "country": "DE",
        "city": "Berlin",
        "latitude": 52.52,
        "longitude": 13.405,
        "radius": 5000,
        "accuracy_m": 5000,
        "randomization": "per_session",
        "randomization_seed": 42,
        "timezone": "Europe/Berlin",
        "locale": "en-GB",
        "languages": ["en-GB", "en"],
        "webrtc_policy": "privacy_enhanced",
    }
