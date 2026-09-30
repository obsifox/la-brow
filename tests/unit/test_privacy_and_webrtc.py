"""Privacy policy and WebRTC preset tests."""

from __future__ import annotations

from privacy.policy import DELEGATED_TO_GECKO, PRESETS, PrivacyPolicy, TriState, preference_map, report
from webrtc.policy import LIMITATION_STATEMENT, WebRtcPolicy, describe, preferences


def test_strict_preset_disables_high_risk_surfaces():
    strict = PRESETS["strict"]
    payload = strict.as_dict()
    assert payload["cookies"] == "disabled"
    assert payload["webrtc_policy"] == WebRtcPolicy.PRIVACY_ENHANCED.value
    assert payload["clipboard"] == "disabled"


def test_privacy_preferences_include_webrtc_preferences():
    mapping = preference_map(PRESETS["strict"])
    assert mapping["media.peerconnection.ice.no_host"] is True
    assert mapping["dom.security.https_only_mode"] is True


def test_gecko_delegation_list_is_explicit():
    assert "tracking-protection-lists" in DELEGATED_TO_GECKO
    assert report(PrivacyPolicy())["duplication_policy"].startswith("controls are expressed")


def test_round_trip_conversion():
    policy = PRESETS["strict"]
    assert PrivacyPolicy.from_dict(policy.as_dict()).as_dict() == policy.as_dict()


def test_webrtc_policies_are_distinct():
    default = preferences(WebRtcPolicy.DEFAULT)
    enhanced = preferences(WebRtcPolicy.PRIVACY_ENHANCED)
    relay = preferences(WebRtcPolicy.DISABLE_LOCAL_CANDIDATES)
    assert default["media.peerconnection.ice.no_host"] is False
    assert enhanced["media.peerconnection.ice.no_host"] is True
    assert relay["media.peerconnection.ice.relay_only"] is True


def test_custom_policy_uses_supplied_preferences():
    assert preferences(WebRtcPolicy.CUSTOM, {"media.peerconnection.enabled": False}) == {"media.peerconnection.enabled": False}


def test_limitation_statement_avoids_anonymity_claims():
    assert "do not guarantee network anonymity" in LIMITATION_STATEMENT
    assert "public IP" in LIMITATION_STATEMENT
    described = describe(WebRtcPolicy.PRIVACY_ENHANCED)
    assert "stun" in described["test_matrix_dimensions"]
    assert "dns" in described["test_matrix_dimensions"]
