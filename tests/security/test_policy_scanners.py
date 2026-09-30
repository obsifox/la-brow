"""Security tests for the repository policy scanners."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tools.scanners.branding_scan import in_user_facing_root, scan_text as branding_scan_text
from tools.scanners.comment_scan import classify, hash_findings, python_comment_findings, scan_file
from tools.scanners.emoji_scan import scan_text as emoji_scan_text
from tools.scanners.english_scan import scan_text as english_scan_text
from tools.scanners.policy_loader import load_branding, load_code_style

REPO_ROOT = Path(__file__).resolve().parents[2]
SLASH = chr(47)


def test_emoji_detection_covers_common_ranges():
    for sample in ("\U0001F600", "\U0001F44D", "\u2728", "\u2600", "\u2764"):
        assert emoji_scan_text(f"value {sample}") != []
    assert emoji_scan_text("plain ascii text") == []


def test_emoji_variation_selector_and_joiner_detected():
    assert emoji_scan_text("a\uFE0Fb") != []
    assert emoji_scan_text("a\u200Db") != []


def test_python_comment_detection_ignores_strings():
    source = 'value = "' + SLASH * 2 + ' not a comment"\n'
    assert python_comment_findings(source) == []
    commented = "# real comment\n"
    assert python_comment_findings(commented) != []


def test_double_slash_is_an_operator_and_not_a_comment_in_python():
    assert python_comment_findings("quotient = total " + SLASH * 2 + " count\n") == []


def test_python_comment_detection_reports_docstrings_as_safe():
    source = '"""Docstring."""\nvalue = 1\n'
    assert python_comment_findings(source) == []


def test_hash_comment_rules_for_yaml():
    assert hash_findings("# comment\n", Path("sample.yaml")) != []
    assert hash_findings("key: value\n", Path("sample.yaml")) == []
    assert hash_findings("value: 'text # not a comment'\n", Path("sample.yaml")) == []


def test_shebang_is_not_a_comment():
    assert hash_findings("#!/usr/bin/env bash\n", Path("sample.sh")) == []


def test_xml_comment_detection():
    markup = "<" + "!" + "-" + "-" + " comment " + "-" + "-" + ">\n"
    assert scan_file(Path("README.md"), "xml") == []
    path = Path(REPO_ROOT / "tests/data/comment-sample.xml")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markup, encoding="utf-8")
    try:
        assert scan_file(path, "xml") != []
    finally:
        path.unlink()


def test_language_classification_by_extension():
    assert classify(Path("a.py")) == "python"
    assert classify(Path("a.yaml")) == "generic-hash"
    assert classify(Path("a.svg")) == "xml"
    assert classify(Path("a.unknown")) is None


def test_english_scanner_reports_foreign_scripts():
    assert english_scan_text("This is English text.") == []
    assert english_scan_text("\u0645\u062a\u0646 \u0639\u0631\u0628\u06cc") != []
    assert english_scan_text("\u4e2d\u6587\u6587\u672c") != []
    assert english_scan_text("\u0420\u0443\u0441\u0441\u043a\u0438\u0439") != []


def test_english_scanner_allows_punctuation_and_accents():
    assert english_scan_text("Quote: \u201cresult\u201d \u2014 note \u2026 ended.") == []
    assert english_scan_text("Caf\u00e9 in Z\u00fcrich") == []


def test_branding_scan_detects_identifier_but_respects_resource_names():
    identifiers = ["acmecorp"]
    violation = branding_scan_text('label: acmecorp browser', identifiers, "ui/strings.xml")
    assert violation != []
    exempt = branding_scan_text('<string name="legal_notice">acmecorp</string>', identifiers, "ui/strings.xml")
    assert exempt == []


def test_branding_scope_configuration_is_explicit():
    branding = load_branding(REPO_ROOT)
    assert branding["product_name"] == "LA Brow"
    assert branding["organization_identifiers"]
    assert in_user_facing_root("ui/screen.html", branding) is True
    assert in_user_facing_root("docs/architecture/system-architecture.md", branding) is False


def test_code_style_exemptions_are_documented():
    style = load_code_style(REPO_ROOT)
    for exemption in style["exemptions"]:
        assert exemption["id"]
        assert exemption["paths"]
        assert exemption["scanners"]
        assert exemption["reason"]
        assert exemption["modification_status"]


def test_repository_scan_state_is_recorded():
    artifacts = REPO_ROOT / ".eng/artifacts"
    if not (artifacts / "comment_scan.json").is_file():
        pytest.skip("scan artifacts are produced by the pipeline run")
    import json

    payload = json.loads((artifacts / "comment_scan.json").read_text(encoding="utf-8"))
    assert payload["status"] in {"PASS", "FAIL"}
    assert "exempted_files" in payload
