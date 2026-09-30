"""Browser scoped timezone resolution built on the IANA time zone database."""

from __future__ import annotations

from datetime import datetime, timezone as timezone_module
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from timezone.errors import InvalidTimezoneError, TimezoneResolutionError
from timezone.models import TimezoneConfig, TimezoneMode, TimezoneResolution

CONTROLLED_SURFACES = (
    "javascript-date-offset",
    "intl-datetimeformat-resolved-options",
    "intl-datetimeformat-parts",
)
UNCONTROLLED_SURFACES = (
    "operating-system-clock",
    "operating-system-date-command",
    "other-applications",
    "file-system-timestamps",
)
KNOWN_ALIASES = {
    "UTC": "UTC",
    "GMT": "Etc/GMT",
    "Z": "UTC",
}


def normalize_zone(name: str) -> str:
    candidate = KNOWN_ALIASES.get(name.strip(), name.strip())
    if candidate in available_timezones():
        return candidate
    raise InvalidTimezoneError("unknown IANA time zone identifier", zone=name)


def is_valid_zone(name: str) -> bool:
    try:
        normalize_zone(name)
    except InvalidTimezoneError:
        return False
    return True


def zone_offset(resolution_moment: datetime, zone_name: str) -> tuple[int, bool, str]:
    target = ZoneInfo(zone_name)
    localized = resolution_moment.astimezone(target)
    delta = localized.utcoffset()
    if delta is None:
        raise TimezoneResolutionError("time zone database returned no offset", zone=zone_name)
    dst = localized.dst()
    dst_active = bool(dst and dst.total_seconds() != 0)
    return int(delta.total_seconds() // 60), dst_active, localized.tzname() or zone_name


def resolve(config: TimezoneConfig, detected_zone: str | None, moment: datetime | None = None) -> TimezoneResolution:
    moment = moment or datetime.now(timezone_module.utc)
    notes: list[str] = []
    if config.mode is TimezoneMode.DISABLED:
        raise TimezoneResolutionError("timezone control is disabled and no browser scoped zone is applied")
    if config.mode is TimezoneMode.MANUAL:
        if not config.zone:
            raise InvalidTimezoneError("manual timezone mode requires a zone")
        zone_name = normalize_zone(config.zone)
        confidence = 1.0
        source = "manual-configuration"
    elif config.mode is TimezoneMode.PROFILE:
        if not config.zone:
            raise InvalidTimezoneError("profile timezone mode requires a zone")
        zone_name = normalize_zone(config.zone)
        confidence = 0.95
        source = f"profile:{config.source_profile or 'unnamed'}"
    else:
        if not detected_zone:
            raise TimezoneResolutionError("automatic timezone mode requires a detected zone")
        zone_name = normalize_zone(detected_zone)
        confidence = 0.7
        source = "automatic-detection"
        notes.append("automatic timezone uses the operating system zone as an environment signal")
    offset_minutes, dst_active, abbreviation = zone_offset(moment, zone_name)
    notes.append("operating system clock is not modified")
    return TimezoneResolution(
        zone=zone_name,
        mode=config.mode,
        offset_minutes=offset_minutes,
        dst_active=dst_active,
        abbreviation=abbreviation,
        confidence=confidence,
        source=source,
        controlled_surfaces=CONTROLLED_SURFACES,
        uncontrolled_surfaces=UNCONTROLLED_SURFACES,
        notes=tuple(notes),
    )


def system_zone_name() -> str | None:
    try:
        link = "/etc/localtime"
        import os

        if os.path.islink(link):
            target = os.readlink(link)
            marker = "zoneinfo/"
            if marker in target:
                return target.split(marker, 1)[1]
    except OSError:
        return None
    timezone_file = "/etc/timezone"
    try:
        with open(timezone_file, encoding="utf-8") as handle:
            value = handle.read().strip()
        if value and is_valid_zone(value):
            return value
    except OSError:
        return None
    return None


def dst_transition_table(zone_name: str, year: int) -> list[dict]:
    zone = ZoneInfo(normalize_zone(zone_name))
    transitions: list[dict] = []
    previous_offset = None
    current = datetime(year, 1, 1, tzinfo=timezone_module.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone_module.utc)
    step = 3600 * 6
    while current <= end:
        localized = current.astimezone(zone)
        offset = localized.utcoffset()
        if previous_offset is not None and offset != previous_offset:
            transitions.append(
                {
                    "utc": current.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "offset_minutes": int(offset.total_seconds() // 60),
                    "dst_active": bool(localized.dst() and localized.dst().total_seconds() != 0),
                }
            )
        previous_offset = offset
        current = current.fromtimestamp(current.timestamp() + step, tz=timezone_module.utc)
    return transitions
