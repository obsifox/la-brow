"""Compatibility layer tests for desktop Firefox themes and add-ons."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from extensions.compat import CompatibilityEngine
from extensions.manifest import ManifestError, parse_manifest
from extensions.policy import evaluate_install
from extensions.store import ExtensionStore, ExtensionStoreError
from extensions.themes import contrast_ratio, parse_color, slugify, theme_spec

REPO_ROOT = Path(__file__).resolve().parents[2]

THEME_MANIFEST = {
    "manifest_version": 2,
    "name": "Neon Grid",
    "version": "1.2.0",
    "type": "theme",
    "theme": {
        "colors": {
            "frame": "#05060A",
            "toolbar": "#12142B",
            "tab_selected": ["#FF2D3F", "#A855F7"],
            "toolbar_text": "#F5F7FF",
            "popup": "#12142B",
            "popup_text": "#F5F7FF",
        },
        "images": {"theme_frame": "header.png"},
        "properties": {"content_color_scheme": "dark"},
    },
}

ADDON_MANIFEST = {
    "manifest_version": 3,
    "name": "Reader Helper",
    "version": "1.0.0",
    "permissions": ["storage", "tabs"],
    "action": {"default_title": "Reader"},
    "content_scripts": [{"matches": ["*://*.example.com/*"], "js": ["reader.js"]}],
}


@pytest.fixture()
def store(tmp_path: Path) -> ExtensionStore:
    return ExtensionStore(REPO_ROOT, root=tmp_path / "extensions")


def test_color_parsing_covers_hex_rgb_and_named_values():
    assert parse_color("#FF2D3F")[:3] == pytest.approx([1.0, 0.176, 0.247], abs=1e-3)
    assert parse_color("#f2d")[:3] == pytest.approx([1.0, 0.133, 0.866], abs=1e-3)
    assert parse_color("rgba(10, 20, 30, 0.5)")[3] == pytest.approx(0.5)
    assert parse_color("transparent")[3] == 0.0
    assert parse_color("not-a-color") is None


def test_slugify_produces_identifier_safe_values():
    assert slugify("Neon Grid 1.2.0") == "neon-grid-1-2-0"
    assert slugify("   ") == "theme"
    assert len(slugify("x" * 90)) <= 63


def test_theme_manifest_is_translated_into_a_gradient_spec():
    spec = theme_spec(parse_manifest(THEME_MANIFEST), "PARTIAL")
    assert spec["source"] == "desktop-firefox-theme"
    assert spec["gradient"]["stops"][0] == "#05060A"
    assert spec["gradient"]["stops"][2] == "#FF2D3F"
    assert spec["gradient"]["accent"] == "#FF2D3F"
    assert spec["gradient"]["accent_glow"].startswith("rgba(255, 45, 63")
    assert spec["palette"]["toolbar"] == "#12142B"
    assert spec["images"]["status"] == "pending-package"
    assert "desktop-theme-applied" in [finding["code"] for finding in spec["findings"]]


def test_theme_without_colors_falls_back_to_the_product_palette():
    manifest = {"manifest_version": 2, "name": "Empty", "version": "0.1.0", "type": "theme", "theme": {"images": {}}}
    spec = theme_spec(parse_manifest(manifest), "PARTIAL")
    assert spec["source"] == "product-default"
    assert spec["gradient"]["stops"][0] == "#0B0C0E"
    assert "theme-colors-absent" in [finding["code"] for finding in spec["findings"]]


def test_low_contrast_theme_is_reported():
    manifest = {
        "manifest_version": 2,
        "name": "Washed",
        "version": "1.0.0",
        "type": "theme",
        "theme": {"colors": {"frame": "#777777", "toolbar": "#7A7A7A", "toolbar_text": "#7C7C7C", "tab_selected": "#7F7F7F"}},
    }
    spec = theme_spec(parse_manifest(manifest), "PARTIAL")
    assert "theme-contrast-low" in [finding["code"] for finding in spec["findings"]]
    assert contrast_ratio(parse_color("#FFFFFF"), parse_color("#000000")) > 20


def test_manifest_parsing_rejects_incomplete_documents():
    with pytest.raises(ManifestError):
        parse_manifest({"manifest_version": 9, "name": "x", "version": "1.0.0"})
    with pytest.raises(ManifestError):
        parse_manifest({"manifest_version": 2, "version": "1.0.0"})
    with pytest.raises(ManifestError):
        parse_manifest({"manifest_version": 2, "name": "Theme Without Section", "version": "1.0.0", "type": "theme"})


def test_addon_with_desktop_only_surfaces_is_partial():
    manifest = {
        "manifest_version": 2,
        "name": "Sidebar Tool",
        "version": "0.4.1",
        "permissions": ["storage", "bookmarks"],
        "sidebar_action": {"default_panel": "panel.html"},
        "chrome_url_overrides": {"newtab": "newtab.html"},
    }
    report = CompatibilityEngine(REPO_ROOT).evaluate(parse_manifest(manifest))
    codes = [finding["code"] for finding in report["findings"]]
    assert report["level"] in {"PARTIAL", "NOT_SUPPORTED"}
    assert "desktop-only-section" in codes
    assert report["notice"], "every installation carries the compatibility notice"
    assert report["notice_required_at_install"] is True


def test_install_policy_refuses_prohibited_permissions_before_acknowledgement():
    manifest = {**ADDON_MANIFEST, "permissions": ["storage", "nativeMessaging"]}
    decision = evaluate_install(REPO_ROOT, manifest, acknowledged=True)
    assert decision["allowed"] is False
    assert decision["code"] == "prohibited_permission"
    assert "nativeMessaging" in decision["context"]["permissions"]


def test_install_policy_requires_the_notice_acknowledgement():
    decision = evaluate_install(REPO_ROOT, ADDON_MANIFEST, acknowledged=False)
    assert decision["allowed"] is False
    assert decision["code"] == "notice_not_acknowledged"
    assert decision["requires_acknowledgement"] is True
    assert evaluate_install(REPO_ROOT, ADDON_MANIFEST, acknowledged=True)["allowed"] is True


def test_store_records_the_notice_and_the_compatibility_level(store: ExtensionStore):
    with pytest.raises(ExtensionStoreError):
        store.install(ADDON_MANIFEST, acknowledged=False)
    record = store.install(ADDON_MANIFEST, acknowledged=True)
    assert record["notice_acknowledged"] is True
    assert record["notice_text"].startswith("This add-on targets desktop Firefox")
    assert record["signature"] == "unverified"
    assert record["manifest_sha256"]
    assert store.list_records()["count"] == 1


def test_store_activates_themes_and_returns_the_product_default_when_empty(store: ExtensionStore):
    assert store.active_theme_spec()["id"] == "product-default"
    theme_record = store.install(THEME_MANIFEST, acknowledged=True)
    assert store.list_records()["active_theme"] == theme_record["id"]
    assert store.active_theme_spec()["gradient"]["stops"][2] == "#FF2D3F"
    addon_record = store.install(ADDON_MANIFEST, acknowledged=True)
    with pytest.raises(ExtensionStoreError):
        store.activate_theme(addon_record["id"])
    assert store.activate_theme(theme_record["id"])["active_theme"] == theme_record["id"]
    assert store.remove(theme_record["id"])["removed"] is True
    assert store.list_records()["active_theme"] is None


def test_store_persists_records_on_disk(tmp_path: Path):
    root = tmp_path / "extensions"
    store = ExtensionStore(REPO_ROOT, root=root)
    store.install(THEME_MANIFEST, acknowledged=True)
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    assert index["schema_version"] == 1
    assert index["extensions"][0]["type"] == "theme"
    assert oct((root / "index.json").stat().st_mode)[-3:] == "600"


def test_matrix_summary_exposes_the_runtime_and_the_notice():
    summary = CompatibilityEngine(REPO_ROOT).matrix_summary()
    assert summary["runtime"]["engine"] == "geckoview"
    assert len(summary["sections"]) >= 10
    assert any(entry["level"] == "unsupported" for entry in summary["sections"])
    assert summary["install_notice"]
