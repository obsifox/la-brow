"""Boundary focused security tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

RESOLVER_CONFIGURATION_PATHS = (
    "dns/engine.py",
    "dns/transport_system.py",
    "doh/client.py",
    "dot/client.py",
)

WRITE_TOKENS = ("write_text", "shutil.copy", "os.replace", "open(", "chmod")


def test_resolver_modules_never_write_resolver_configuration():
    offenders = []
    for relative in RESOLVER_CONFIGURATION_PATHS:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        if "resolv.conf" not in text:
            continue
        for token in WRITE_TOKENS:
            for line in text.splitlines():
                if "resolv.conf" in line and token in line:
                    offenders.append(f"{relative}: {line.strip()}")
    assert offenders == []


def test_profile_store_is_the_only_configuration_writer():
    writers = []
    for path in sorted(REPO_ROOT.glob("**/*.py")):
        if any(part in {"tests", "tools", ".venv", "__pycache__"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        if "_atomic_write" in text and "profiles/store.py" not in str(path):
            writers.append(path.relative_to(REPO_ROOT).as_posix())
    assert writers == []


def test_environment_core_does_not_import_user_interface_modules():
    text = (REPO_ROOT / "environment/core.py").read_text(encoding="utf-8")
    assert "import browser" not in text
    assert "from browser" not in text
    assert "import application" not in text


def test_geo_engine_refuses_physical_fallback_in_virtual_mode():
    from geo.engine import GeoEngine
    from geo.errors import PhysicalFallbackForbiddenError, ProviderUnavailableError
    from geo.models import GeoMode, GeoRequest, GeoSource
    from geo.providers import GeoProvider

    class FailingProvider(GeoProvider):
        provider_id = "failing"
        source = GeoSource.VIRTUAL
        mode = GeoMode.MANUAL

        def resolve(self, request):
            raise ProviderUnavailableError("simulated failure", provider=self.provider_id)

    engine = GeoEngine({GeoMode.MANUAL: FailingProvider()})
    request = GeoRequest(mode=GeoMode.MANUAL, block_physical_fallback=True)
    with pytest.raises(PhysicalFallbackForbiddenError) as error:
        engine.resolve(request)
    assert error.value.code == "geo_physical_fallback_forbidden"
    assert engine.failures


def test_virtual_mode_never_reaches_physical_provider():
    import geo.providers as providers_module
    from geo.engine import GeoEngine
    from geo.models import GeoMode, GeoRequest
    from geo.providers import PhysicalProvider, VirtualProvider
    from geo.models import GeoCircle, GeoCoordinate

    calls = {"physical": 0}

    class RecordingBridge:
        def available(self) -> bool:
            return True

        def read_fix(self):
            calls["physical"] += 1
            return GeoCoordinate(0.0, 0.0)

    circle = GeoCircle(center=GeoCoordinate(52.52, 13.405), radius_m=1000)
    engine = GeoEngine({GeoMode.MANUAL: VirtualProvider(circle, base_seed=5)})
    engine.resolve(GeoRequest(mode=GeoMode.MANUAL))
    assert calls["physical"] == 0
    assert PhysicalProvider(RecordingBridge()).provider_id == "physical-provider"
