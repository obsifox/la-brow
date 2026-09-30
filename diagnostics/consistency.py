"""Environment consistency diagnostics across browser visible surfaces."""

from __future__ import annotations

from geo.dataset import country_entry

STATEMENT = (
    "Consistency diagnostics report observable mismatches between environment surfaces. "
    "They are diagnostic only and do not guarantee fingerprint anonymity."
)

SEVERITY_ORDER = {"INFO": 0, "WARN": 1, "HIGH": 2}


def finding(identifier: str, severity: str, message: str, surfaces: list[str], suggestion: str) -> dict:
    return {
        "id": identifier,
        "severity": severity,
        "message": message,
        "surfaces": surfaces,
        "suggestion": suggestion,
    }


def check(profile: dict, geo_fix: dict | None, timezone_resolution: dict | None, locale_resolution: dict | None, dns_status: dict | None) -> dict:
    findings: list[dict] = []
    geo_country = (profile or {}).get("country")
    geo_entry = country_entry(geo_country) if geo_country else None
    if geo_fix and timezone_resolution:
        zone_owner = None
        for code, entry in _country_table().items():
            if entry.get("timezone") == timezone_resolution.get("zone"):
                zone_owner = code
                break
        if zone_owner and geo_country and zone_owner != geo_country:
            findings.append(
                finding(
                    "timezone-location-mismatch",
                    "WARN",
                    f"virtual location country {geo_country} does not match the country that commonly uses {timezone_resolution.get('zone')}",
                    ["location", "timezone"],
                    "align the profile timezone with the selected location or document the intentional mismatch",
                )
            )
    if geo_country and locale_resolution:
        surfaces = locale_resolution.get("surfaces", {})
        browser_locale = surfaces.get("browser_locale", "")
        parts = browser_locale.replace("_", "-").split("-")
        region = parts[1].upper() if len(parts) > 1 else None
        if region and region != geo_country:
            findings.append(
                finding(
                    "locale-region-mismatch",
                    "WARN",
                    f"browser locale region {region} does not match the virtual location country {geo_country}",
                    ["location", "locale"],
                    "review the language preference order for this profile",
                )
            )
    if dns_status:
        if dns_status.get("resolver_protocol") in {"system", "custom"} and profile.get("doh"):
            findings.append(
                finding(
                    "resolver-mode-declared-but-not-active",
                    "HIGH",
                    "the profile declares an encrypted resolver while the active resolver protocol is not encrypted",
                    ["dns", "privacy"],
                    "activate the declared resolver profile or update the profile declaration",
                )
            )
        if not dns_status.get("system_resolver_unchanged", True):
            findings.append(
                finding(
                    "system-resolver-modified",
                    "HIGH",
                    "operating system resolver configuration changed while the browser was running",
                    ["dns", "operating-system"],
                    "restore the operating system resolver configuration and investigate the change",
                )
            )
    if geo_entry and geo_fix:
        coordinate = geo_fix.get("coordinate", {})
        latitude = coordinate.get("latitude")
        longitude = coordinate.get("longitude")
        if latitude is not None and longitude is not None:
            from geo.geodesy import haversine_distance_m
            from geo.models import GeoCoordinate

            distance = haversine_distance_m(
                GeoCoordinate(latitude=geo_entry["latitude"], longitude=geo_entry["longitude"]),
                GeoCoordinate(latitude=latitude, longitude=longitude),
            )
            if distance > 1500000.0:
                findings.append(
                    finding(
                        "coordinate-country-distance",
                        "WARN",
                        f"resolved coordinate is approximately {round(distance / 1000.0)} km away from the declared country centroid",
                        ["location"],
                        "confirm the intended location radius and country selection",
                    )
                )
    highest = "INFO"
    for entry in findings:
        if SEVERITY_ORDER[entry["severity"]] > SEVERITY_ORDER[highest]:
            highest = entry["severity"]
    return {
        "status": "CONSISTENT" if not findings else "POTENTIAL_MISMATCH",
        "highest_severity": highest,
        "findings": findings,
        "statement": STATEMENT,
    }


def _country_table() -> dict:
    from geo.dataset import load_countries

    return load_countries()
