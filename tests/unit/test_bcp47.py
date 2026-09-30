"""BCP 47 parsing tests."""

from __future__ import annotations

import pytest

from locale_engine.bcp47 import InvalidLanguageTagError, canonicalize, is_valid, matches_region_free, parse


@pytest.mark.parametrize(
    "tag",
    ["en", "en-US", "de-DE", "zh-Hant", "sr-Latn-RS", "en-GB-oed", "x-private"],
)
def test_valid_tags_are_accepted(tag):
    assert is_valid(tag) is True


@pytest.mark.parametrize("tag", ["", "e", "123", "en_US_extra_long_subtag_that_is_too_long_for_bcp47_rules", "-", "en--US"])
def test_invalid_tags_are_rejected(tag):
    assert is_valid(tag) is False


def test_canonical_form_normalizes_case():
    assert canonicalize("EN-us") == "en-US"
    assert canonicalize("de-de") == "de-DE"
    assert canonicalize("zh-hant") == "zh-Hant"


def test_script_and_region_are_parsed():
    tag = parse("sr-Latn-RS")
    assert tag.language == "sr"
    assert tag.script == "Latn"
    assert tag.region == "RS"


def test_long_tag_is_rejected():
    with pytest.raises(InvalidLanguageTagError):
        parse("en-" + "x" * 80)


def test_region_free_matching():
    assert matches_region_free("en-GB", "en") is True
    assert matches_region_free("de-DE", "en") is False
