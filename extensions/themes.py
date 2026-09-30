"""Theme translation from desktop Firefox theme manifests to product theme specifications."""

from __future__ import annotations

import re
from statistics import mean

from extensions.manifest import WebExtensionManifest

PRODUCT_PALETTE = {
    "frame": "#0B0C0E",
    "frame_inactive": "#0B0C0E",
    "toolbar": "#14161A",
    "toolbar_text": "#FFFFFF",
    "toolbar_field": "#1B1E24",
    "toolbar_field_text": "#FFFFFF",
    "toolbar_field_border": "#2A2F38",
    "tab_selected": "#FF2D3F",
    "tab_text": "#FFFFFF",
    "tab_background_text": "#C7CBD3",
    "popup": "#14161A",
    "popup_text": "#FFFFFF",
    "popup_border": "#2A2F38",
    "sidebar": "#0F1115",
    "sidebar_text": "#E7E9EE",
    "button_background_hover": "#A855F7",
    "button_color": "#FFFFFF",
    "icons": "#FFFFFF",
    "ntp_background": "#0B0C0E",
    "ntp_text": "#FFFFFF",
}
THEME_COLOR_KEYS = tuple(PRODUCT_PALETTE.keys())
POPUP_GRADIENT_KEYS = ("tab_selected", "button_background_hover")
NAMED_COLORS = {
    "transparent": [0.0, 0.0, 0.0, 0.0],
    "black": [0.0, 0.0, 0.0, 1.0],
    "white": [1.0, 1.0, 1.0, 1.0],
}
SLUG_ALLOWED = re.compile(r"[^a-z0-9-]+")
HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
RGB = re.compile(r"^rgba?\(([^)]+)\)$")


class ThemeSpecError(Exception):
    """Raised when a theme manifest cannot be translated."""

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message)
        self.code = "theme_invalid"
        self.message = message
        self.context = dict(context)

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "context": self.context}


def slugify(value: str) -> str:
    candidate = SLUG_ALLOWED.sub("-", value.strip().lower()).strip("-")
    candidate = candidate[:63].strip("-")
    return candidate or "theme"


def parse_color(value: object) -> list[float] | None:
    if isinstance(value, list):
        for entry in value:
            parsed = parse_color(entry)
            if parsed is not None:
                return parsed
        return None
    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if lowered in NAMED_COLORS:
            return list(NAMED_COLORS[lowered])
        match = HEX.match(text)
        if match:
            digits = match.group(1)
            if len(digits) == 3:
                digits = "".join(character * 2 for character in digits)
            channels = [int(digits[index : index + 2], 16) / 255.0 for index in (0, 2, 4)]
            alpha = int(digits[6:8], 16) / 255.0 if len(digits) == 8 else 1.0
            return [*channels, alpha]
        match = RGB.match(text)
        if match:
            parts = [part.strip() for part in match.group(1).split(",")]
            if len(parts) in (3, 4):
                channels = []
                for part in parts[:3]:
                    channels.append(int(round(float(part.rstrip("%")))) / 255.0 if part.endswith("%") else float(part) / 255.0)
                alpha = float(parts[3]) if len(parts) == 4 else 1.0
                return [*channels, max(0.0, min(1.0, alpha))]
    return None


def to_hex(channels: list[float]) -> str:
    values = [max(0.0, min(1.0, channel)) for channel in channels[:3]]
    return "#" + "".join(f"{int(round(value * 255)):02X}" for value in values)


def blend(first: list[float], second: list[float], ratio: float) -> list[float]:
    amount = max(0.0, min(1.0, ratio))
    return [first[index] * (1 - amount) + second[index] * amount for index in range(3)] + [1.0]


def alpha(channels: list[float], value: float) -> str:
    red, green, blue = (int(round(channel * 255)) for channel in channels[:3])
    return f"rgba({red}, {green}, {blue}, {round(value, 3)})"


def relative_luminance(channels: list[float]) -> float:
    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in channels[:3])
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: list[float], second: list[float]) -> float:
    light, dark = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return round((light + 0.05) / (dark + 0.05), 2)


def _collect_colors(theme: dict) -> dict[str, list[float]]:
    declared = theme.get("colors") if isinstance(theme.get("colors"), dict) else {}
    resolved: dict[str, list[float]] = {}
    for key in THEME_COLOR_KEYS:
        parsed = parse_color(declared.get(key))
        if parsed is not None:
            resolved[key] = parsed
    return resolved


def _gradient_stops(palette_colors: dict[str, list[float]], declared_colors: dict[str, list[float]]) -> list[str]:
    stops: list[str] = []
    for key in ("frame", "toolbar", "tab_selected"):
        source = declared_colors.get(key) or palette_colors.get(key)
        if source is not None:
            stops.append(to_hex(source))
    if len(stops) < 2:
        stops = [PRODUCT_PALETTE["frame"], PRODUCT_PALETTE["toolbar"], PRODUCT_PALETTE["tab_selected"]]
    return stops


def _contrast_findings(palette_colors: dict[str, list[float]]) -> list[dict]:
    findings: list[dict] = []
    pairs = (
        ("toolbar_text", "toolbar"),
        ("tab_text", "tab_selected"),
        ("popup_text", "popup"),
        ("sidebar_text", "sidebar"),
    )
    for text_key, background_key in pairs:
        text_color = palette_colors.get(text_key)
        background_color = palette_colors.get(background_key)
        if text_color is None or background_color is None:
            continue
        ratio = contrast_ratio(text_color, background_color)
        if ratio < 3.0:
            findings.append(
                {
                    "code": "theme-contrast-low",
                    "severity": "WARN",
                    "message": f"contrast between {text_key} and {background_key} is {ratio}, text may be unreadable",
                }
            )
        elif ratio < 4.5:
            findings.append(
                {
                    "code": "theme-contrast-advisory",
                    "severity": "NOTICE",
                    "message": f"contrast between {text_key} and {background_key} is {ratio}, below the recommended reading ratio",
                }
            )
    return findings


def theme_spec(manifest: WebExtensionManifest, compatible_level: str = "PARTIAL") -> dict:
    if manifest.type != "theme" or not manifest.theme:
        raise ThemeSpecError("manifest does not declare a theme")
    theme = manifest.theme
    declared_colors = _collect_colors(theme)
    palette_colors: dict[str, list[float]] = {}
    for key in THEME_COLOR_KEYS:
        default = parse_color(PRODUCT_PALETTE[key]) or [0.0, 0.0, 0.0, 1.0]
        palette_colors[key] = declared_colors.get(key, default)
    palette = {key: to_hex(value) for key, value in palette_colors.items()}
    images = theme.get("images") if isinstance(theme.get("images"), dict) else {}
    properties = theme.get("properties") if isinstance(theme.get("properties"), dict) else {}
    frame_image = images.get("theme_frame")
    findings: list[dict] = list(_contrast_findings(palette_colors))
    if frame_image:
        findings.append(
            {
                "code": "theme-frame-image-pending",
                "severity": "NOTICE",
                "message": "the theme declares a background image, which is applied only when the packaged theme is provided",
                "detail": str(frame_image),
            }
        )
    if not declared_colors:
        findings.append(
            {
                "code": "theme-colors-absent",
                "severity": "NOTICE",
                "message": "the theme declares no colours, the product palette is used",
            }
        )
    if declared_colors:
        findings.append(
            {
                "code": "desktop-theme-applied",
                "severity": "NOTICE",
                "message": "colours are translated from a desktop Firefox theme, layout level styling is not applied",
            }
        )
    stops = _gradient_stops(palette_colors, declared_colors)
    accent_color = declared_colors.get("tab_selected") or palette_colors["tab_selected"]
    glow_color = declared_colors.get("button_background_hover") or blend(accent_color, palette_colors["frame"], 0.35)
    return {
        "id": slugify(f"{manifest.name}-{manifest.version}"),
        "name": manifest.name,
        "version": manifest.version,
        "source": "desktop-firefox-theme" if declared_colors else "product-default",
        "origin": "firefox-desktop-theme-manifest",
        "runtime_compatibility": compatible_level,
        "palette": palette,
        "gradient": {
            "angle_degrees": 135,
            "stops": stops,
            "accent": to_hex(accent_color),
            "accent_glow": alpha(accent_color, 0.35),
            "glow": to_hex(glow_color),
            "average": to_hex([mean([parse_color(stop)[index] for stop in stops]) for index in range(3)]),
        },
        "properties": {
            "color_scheme": properties.get("color_scheme", "dark"),
            "content_color_scheme": properties.get("content_color_scheme", "dark"),
        },
        "images": {"theme_frame": frame_image, "status": "pending-package" if frame_image else "none"},
        "findings": findings,
        "declared_color_keys": sorted(declared_colors.keys()),
    }
