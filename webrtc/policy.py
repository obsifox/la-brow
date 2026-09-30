"""WebRTC policy presets and their tested limits."""

from __future__ import annotations

from enum import Enum

LIMITATION_STATEMENT = (
    "WebRTC policy presets reduce specific candidate exposure surfaces; they do not guarantee network anonymity "
    "and they do not change the public IP address observed by remote peers."
)

TEST_MATRIX_DIMENSIONS = (
    "stun",
    "turn",
    "ipv4",
    "ipv6",
    "proxy",
    "vpn",
    "dns",
)


class WebRtcPolicy(str, Enum):
    DEFAULT = "default"
    PRIVACY_ENHANCED = "privacy_enhanced"
    DISABLE_LOCAL_CANDIDATES = "disable_local_candidates"
    CUSTOM = "custom"


POLICY_PREFERENCE_MAP = {
    WebRtcPolicy.DEFAULT: {
        "media.peerconnection.enabled": True,
        "media.peerconnection.ice.no_host": False,
        "media.peerconnection.ice.default_address_only": False,
        "media.peerconnection.ice.proxy_only_if_behind_proxy": False,
    },
    WebRtcPolicy.PRIVACY_ENHANCED: {
        "media.peerconnection.enabled": True,
        "media.peerconnection.ice.no_host": True,
        "media.peerconnection.ice.default_address_only": True,
        "media.peerconnection.ice.proxy_only_if_behind_proxy": True,
    },
    WebRtcPolicy.DISABLE_LOCAL_CANDIDATES: {
        "media.peerconnection.enabled": True,
        "media.peerconnection.ice.no_host": True,
        "media.peerconnection.ice.default_address_only": True,
        "media.peerconnection.ice.proxy_only_if_behind_proxy": True,
        "media.peerconnection.ice.relay_only": True,
    },
    WebRtcPolicy.CUSTOM: {},
}


def preferences(policy: WebRtcPolicy, custom: dict | None = None) -> dict:
    if policy is WebRtcPolicy.CUSTOM:
        return dict(custom or {})
    return dict(POLICY_PREFERENCE_MAP[policy])


def describe(policy: WebRtcPolicy) -> dict:
    return {
        "policy": policy.value,
        "preferences": preferences(policy),
        "limitation_statement": LIMITATION_STATEMENT,
        "test_matrix_dimensions": list(TEST_MATRIX_DIMENSIONS),
        "documentation_reference": "docs/security/network-security.md",
    }
