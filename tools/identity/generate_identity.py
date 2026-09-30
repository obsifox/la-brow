"""Generate the vector and raster identity assets for the product."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

VIEWBOX = 512
SUPERSAMPLE = 4
RASTER_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)

WHITE = "#FFFFFF"
BLACK = "#0B0C0E"
RED = "#FF2D3F"
PURPLE = "#A855F7"
OUTLINE_DARK = "#E6E8EC"
OUTLINE_LIGHT = "#0B0C0E"

LEFT_HALF = [(256, 128), (196, 152), (96, 72), (60, 208), (74, 320), (152, 404), (256, 464)]
RIGHT_HALF = [(256, 128), (316, 152), (416, 72), (452, 208), (438, 320), (360, 404), (256, 464)]
LEFT_EYE = (176, 244)
RIGHT_EYE = (336, 244)
EYE_RADIUS = 44
PUPIL_RADIUS = 15
LEFT_PUPIL = (188, 232)
RIGHT_PUPIL = (324, 232)
EYE_HIGHLIGHT_RADIUS = PUPIL_RADIUS
LEFT_HIGHLIGHT = LEFT_PUPIL
RIGHT_HIGHLIGHT = RIGHT_PUPIL
NOSE = [(256, 448), (226, 396), (286, 396)]
MUZZLE_LEFT = [(256, 448), (226, 396), (256, 396)]
MUZZLE_RIGHT = [(256, 448), (286, 396), (256, 396)]
OUTLINE_STROKE = 10


def points_to_path(points: list[tuple[int, int]], close: bool = True) -> str:
    commands = [f"M{points[0][0]},{points[0][1]}"]
    for x, y in points[1:]:
        commands.append(f"L{x},{y}")
    if close:
        commands.append("Z")
    return " ".join(commands)


def circle_element(center: tuple[int, int], radius: int, fill: str) -> str:
    return f'<circle cx="{center[0]}" cy="{center[1]}" r="{radius}" fill="{fill}"/>'


def silhouette_points() -> list[tuple[int, int]]:
    return [(96, 72), (196, 152), (256, 128), (316, 152), (416, 72), (452, 208), (438, 320), (360, 404), (256, 464), (152, 404), (74, 320), (60, 208)]


def silhouette_path() -> str:
    return points_to_path(silhouette_points())


def svg_document(body: str, title: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {VIEWBOX} {VIEWBOX}" width="512" height="512" role="img">\n'
        f"<title>{title}</title>\n"
        f"{body}\n"
        "</svg>\n"
    )


def two_tone_body(left_eye_color: str = RED, right_eye_color: str = PURPLE, outline: str | None = None) -> str:
    elements = [
        f'<path d="{points_to_path(LEFT_HALF)}" fill="{WHITE}"/>',
        f'<path d="{points_to_path(RIGHT_HALF)}" fill="{BLACK}"/>',
        f'<path d="{points_to_path(MUZZLE_LEFT)}" fill="{BLACK}"/>',
        f'<path d="{points_to_path(MUZZLE_RIGHT)}" fill="{WHITE}"/>',
        circle_element(LEFT_EYE, EYE_RADIUS, left_eye_color),
        circle_element(RIGHT_EYE, EYE_RADIUS, right_eye_color),
        circle_element(LEFT_HIGHLIGHT, EYE_HIGHLIGHT_RADIUS, BLACK),
        circle_element(RIGHT_HIGHLIGHT, EYE_HIGHLIGHT_RADIUS, WHITE),
        f'<path d="{silhouette_path()}" fill="none" stroke="{outline or OUTLINE_LIGHT}" stroke-width="{OUTLINE_STROKE}" stroke-linejoin="round"/>',
    ]
    return "\n".join(elements)


def symbol_body() -> str:
    elements = [
        f'<path d="{points_to_path(LEFT_HALF)}" fill="{WHITE}"/>',
        f'<path d="{points_to_path(RIGHT_HALF)}" fill="{BLACK}"/>',
        circle_element(LEFT_EYE, EYE_RADIUS + 8, RED),
        circle_element(RIGHT_EYE, EYE_RADIUS + 8, PURPLE),
        f'<path d="{silhouette_path()}" fill="none" stroke="{OUTLINE_LIGHT}" stroke-width="14" stroke-linejoin="round"/>',
    ]
    return "\n".join(elements)


def mask_body() -> str:
    return f'<path d="{silhouette_path()}" fill="{WHITE}"/>'


def monochrome_body() -> str:
    return (
        f'<path d="{silhouette_path()}" fill="currentColor"/>'
        f'\n<path d="{points_to_path(LEFT_HALF)}" fill="none" stroke="#000000" stroke-opacity="0.25" stroke-width="8"/>'
        f'\n<circle cx="{LEFT_EYE[0]}" cy="{LEFT_EYE[1]}" r="{EYE_RADIUS}" fill="none" stroke="#000000" stroke-opacity="0.45" stroke-width="14"/>'
        f'\n<circle cx="{RIGHT_EYE[0]}" cy="{RIGHT_EYE[1]}" r="{EYE_RADIUS}" fill="none" stroke="#FFFFFF" stroke-opacity="0.85" stroke-width="14"/>'
    )


def write_svg(path: Path, body: str, title: str) -> None:
    path.write_text(svg_document(body, title), encoding="utf-8")


def rasterize(size: int, dark_background: bool) -> Image.Image:
    scale = (size * SUPERSAMPLE) / VIEWBOX
    canvas = Image.new("RGBA", (size * SUPERSAMPLE, size * SUPERSAMPLE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    def scaled(points: list[tuple[int, int]]) -> list[tuple[float, float]]:
        return [(x * scale, y * scale) for x, y in points]

    def scaled_circle(center: tuple[int, int], radius: int) -> tuple[float, float, float, float]:
        x, y = center
        return ((x - radius) * scale, (y - radius) * scale, (x + radius) * scale, (y + radius) * scale)

    draw.polygon(scaled(LEFT_HALF), fill=WHITE)
    draw.polygon(scaled(RIGHT_HALF), fill=BLACK)
    draw.polygon(scaled(MUZZLE_LEFT), fill=BLACK)
    draw.polygon(scaled(MUZZLE_RIGHT), fill=WHITE)
    draw.ellipse(scaled_circle(LEFT_EYE, EYE_RADIUS), fill=RED)
    draw.ellipse(scaled_circle(RIGHT_EYE, EYE_RADIUS), fill=PURPLE)
    draw.ellipse(scaled_circle(LEFT_PUPIL, PUPIL_RADIUS), fill=BLACK)
    draw.ellipse(scaled_circle(RIGHT_PUPIL, PUPIL_RADIUS), fill=WHITE)
    outline_color = OUTLINE_DARK if dark_background else OUTLINE_LIGHT
    width = max(2, int(OUTLINE_STROKE * scale))
    draw.line(scaled(silhouette_points()) + [scaled(silhouette_points())[0]], fill=outline_color, width=width, joint="curve")
    return canvas.resize((size, size), Image.LANCZOS)


def eye_visibility_report() -> list[dict]:
    entries = []
    for size in RASTER_SIZES:
        scale = size / VIEWBOX
        diameter = EYE_RADIUS * 2 * scale
        separation = (RIGHT_EYE[0] - LEFT_EYE[0]) * scale
        entries.append(
            {
                "size": size,
                "eye_diameter_px": round(diameter, 2),
                "eye_separation_px": round(separation, 2),
                "eyes_distinguishable": diameter >= 1.8 and separation >= 4.0,
            }
        )
    return entries


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(repo: Path) -> dict:
    identity = repo / "assets/identity"
    generated = identity / "generated"
    identity.mkdir(parents=True, exist_ok=True)
    generated.mkdir(parents=True, exist_ok=True)
    write_svg(identity / "icon.svg", two_tone_body(), "Product identity mark")
    write_svg(identity / "icon-symbol.svg", symbol_body(), "Product identity symbol")
    write_svg(identity / "icon-mask.svg", mask_body(), "Product identity mask")
    write_svg(identity / "icon-monochrome.svg", monochrome_body(), "Product identity monochrome")
    write_svg(identity / "icon-dark.svg", two_tone_body(outline=OUTLINE_DARK), "Product identity for dark surfaces")
    write_svg(identity / "icon-light.svg", two_tone_body(outline=OUTLINE_LIGHT), "Product identity for light surfaces")
    write_svg(identity / "icon-outline.svg", two_tone_body(outline=OUTLINE_DARK), "Product identity outline variant")
    artifacts = []
    for size in RASTER_SIZES:
        raster = rasterize(size, dark_background=False)
        target = generated / f"icon-{size}.png"
        raster.save(target)
        artifacts.append({"size": size, "path": str(target.relative_to(repo)), "sha256": file_digest(target)})
    report = {
        "viewbox": VIEWBOX,
        "palette": {"white": WHITE, "black": BLACK, "red": RED, "purple": PURPLE},
        "svg_assets": [
            "assets/identity/icon.svg",
            "assets/identity/icon-symbol.svg",
            "assets/identity/icon-mask.svg",
            "assets/identity/icon-monochrome.svg",
            "assets/identity/icon-dark.svg",
            "assets/identity/icon-light.svg",
        ],
        "rasters": artifacts,
        "eye_visibility": eye_visibility_report(),
        "policy": {
            "contains_text": False,
            "contains_watermark": False,
            "contains_organization_name": False,
            "svg_metadata_language": "English",
        },
    }
    (identity / "identity-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate identity assets")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--check", action="store_true", help="report legibility without writing files")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    if arguments.check:
        report = {"eye_visibility": eye_visibility_report()}
    else:
        report = generate(repo)
    failures = [entry for entry in report["eye_visibility"] if not entry["eyes_distinguishable"]]
    print(f"identity assets generated={len(report.get('rasters', []))} legibility_failures={len(failures)}")
    for entry in report["eye_visibility"]:
        print(f"  {entry['size']:>4}px eye_diameter={entry['eye_diameter_px']}px separation={entry['eye_separation_px']}px ok={entry['eyes_distinguishable']}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
