"""Central privacy policy engine that delegates to Gecko instead of duplicating it."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum

from webrtc.policy import WebRtcPolicy

DELEGATED_TO_GECKO = (
    "tracking-protection-lists",
    "cookie-jar-implementation",
    "storage-partitioning",
    "https-first-upgrade",
    "permission-prompts",
    "download-protection",
    "certificate-validation",
)


class TriState(str, Enum):
    INHERIT = "inherit"
    ENABLED = "enabled"
    DISABLED = "disabled"


class ReferrerPolicy(str, Enum):
    INHERIT = "inherit"
    STRICT_ORIGIN = "strict-origin"
    STRICT_ORIGIN_WHEN_CROSS_ORIGIN = "strict-origin-when-cross-origin"
    NO_REFERRER = "no-referrer"


@dataclass
class PrivacyPolicy:
    cookies: TriState = TriState.INHERIT
    storage: TriState = TriState.INHERIT
    permissions: TriState = TriState.INHERIT
    referrer: ReferrerPolicy = ReferrerPolicy.INHERIT
    tracking_protection: TriState = TriState.INHERIT
    fingerprinting_protection: TriState = TriState.INHERIT
    webrtc_policy: WebRtcPolicy = WebRtcPolicy.DEFAULT
    geolocation: TriState = TriState.INHERIT
    dns: TriState = TriState.INHERIT
    https_only: TriState = TriState.INHERIT
    downloads: TriState = TriState.INHERIT
    clipboard: TriState = TriState.INHERIT
    notifications: TriState = TriState.INHERIT
    camera: TriState = TriState.INHERIT
    microphone: TriState = TriState.INHERIT
    custom: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        payload = asdict(self)
        for key, value in list(payload.items()):
            if isinstance(value, Enum):
                payload[key] = value.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "PrivacyPolicy":
        converted = dict(payload)
        for key, value in list(converted.items()):
            if key == "webrtc_policy":
                converted[key] = WebRtcPolicy(value)
            elif key == "referrer":
                converted[key] = ReferrerPolicy(value)
            elif key in {field_name for field_name in cls.__dataclass_fields__ if field_name not in {"custom", "webrtc_policy", "referrer"}}:
                if isinstance(value, str):
                    converted[key] = TriState(value)
        return cls(**converted)


PRESETS = {
    "balanced": PrivacyPolicy(),
    "strict": PrivacyPolicy(
        cookies=TriState.DISABLED,
        storage=TriState.DISABLED,
        referrer=ReferrerPolicy.NO_REFERRER,
        tracking_protection=TriState.ENABLED,
        fingerprinting_protection=TriState.ENABLED,
        webrtc_policy=WebRtcPolicy.PRIVACY_ENHANCED,
        https_only=TriState.ENABLED,
        clipboard=TriState.DISABLED,
        notifications=TriState.DISABLED,
        camera=TriState.DISABLED,
        microphone=TriState.DISABLED,
    ),
    "development": PrivacyPolicy(
        tracking_protection=TriState.DISABLED,
        fingerprinting_protection=TriState.DISABLED,
    ),
}


def preference_map(policy: PrivacyPolicy) -> dict:
    mapping = {
        "privacy.trackingprotection.enabled": policy.tracking_protection is TriState.ENABLED,
        "privacy.resistFingerprinting": policy.fingerprinting_protection is TriState.ENABLED,
        "network.cookie.cookieBehavior": 2 if policy.cookies is TriState.DISABLED else 0,
        "dom.storage.enabled": policy.storage is not TriState.DISABLED,
        "network.http.referer.XOriginPolicy": 2 if policy.referrer is ReferrerPolicy.NO_REFERRER else 0,
        "permissions.default.geo": 2 if policy.geolocation is TriState.DISABLED else 0,
        "dom.webnotifications.enabled": policy.notifications is not TriState.DISABLED,
        "media.navigator.enabled": policy.camera is not TriState.DISABLED or policy.microphone is not TriState.DISABLED,
        "dom.event.clipboardevents.enabled": policy.clipboard is not TriState.DISABLED,
        "dom.security.https_only_mode": policy.https_only is TriState.ENABLED,
    }
    from webrtc.policy import preferences as webrtc_preferences

    mapping.update(webrtc_preferences(policy.webrtc_policy))
    return mapping


def report(policy: PrivacyPolicy) -> dict:
    return {
        "policy": policy.as_dict(),
        "preferences": preference_map(policy),
        "delegated_to_gecko": list(DELEGATED_TO_GECKO),
        "duplication_policy": "controls are expressed as preferences and policies rather than reimplemented inside the environment core",
    }
