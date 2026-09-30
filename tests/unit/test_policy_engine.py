"""Per site policy precedence tests."""

from __future__ import annotations

from policy.engine import resolve, validate_rule
from policy.models import PolicyScope, SiteRule


def rules() -> list[SiteRule]:
    return [
        SiteRule(id="global-timezone", scope=PolicyScope.GLOBAL, pattern="*", overrides={"timezone": "UTC"}),
        SiteRule(id="domain-example", scope=PolicyScope.DOMAIN, pattern="example.com", overrides={"timezone": "Europe/Berlin", "locale": "en-GB"}),
        SiteRule(id="subdomain-app", scope=PolicyScope.SUBDOMAIN, pattern="example.com", overrides={"locale": "de-DE"}),
        SiteRule(id="origin-app", scope=PolicyScope.ORIGIN, pattern="https://app.example.com", overrides={"radius": 1000}),
        SiteRule(id="browsing-private", scope=PolicyScope.PRIVATE_BROWSING, pattern="*", overrides={"randomization": "per_query"}),
        SiteRule(id="browsing-normal", scope=PolicyScope.NORMAL_BROWSING, pattern="*", overrides={"randomization": "none"}),
        SiteRule(id="disabled-rule", scope=PolicyScope.ORIGIN, pattern="https://app.example.com", overrides={"locale": "fr-FR"}, enabled=False),
    ]


def test_origin_scope_wins_over_domain_scope():
    resolution = resolve(rules(), "https://app.example.com/page")
    assert resolution.effective_overrides["timezone"] == "Europe/Berlin"
    assert resolution.effective_overrides["locale"] == "de-DE"
    assert resolution.effective_overrides["radius"] == 1000
    assert resolution.unmatched is False


def test_normal_browsing_overrides_private_rule():
    resolution = resolve(rules(), "https://app.example.com/page", private_browsing=False)
    assert resolution.effective_overrides["randomization"] == "none"


def test_private_browsing_selects_private_rule():
    resolution = resolve(rules(), "https://app.example.com/page", private_browsing=True)
    assert resolution.effective_overrides["randomization"] == "per_query"


def test_unmatched_url_uses_global_scope_by_default():
    resolution = resolve(rules(), "https://other.test/")
    assert resolution.effective_overrides["timezone"] == "UTC"


def test_trace_is_recorded_for_every_field():
    resolution = resolve(rules(), "https://app.example.com/page")
    fields = {entry["field"] for entry in resolution.trace}
    assert {"timezone", "locale", "radius", "*"} <= fields
    overrides = [entry for entry in resolution.trace if entry["decision"] == "replaces-lower-specificity-value"]
    assert any(entry["previous_value"] == "UTC" and entry["rule_id"] == "domain-example" for entry in overrides)


def test_precedence_order_is_documented_in_trace():
    entry = [item for item in resolve(rules(), "https://app.example.com/").trace if item["field"] == "*"][0]
    assert entry["precedence_order"].startswith("origin > subdomain > domain")


def test_deterministic_ordering_is_stable():
    first = resolve(rules(), "https://app.example.com/page").effective_overrides
    second = resolve(rules(), "https://app.example.com/page").effective_overrides
    assert first == second


def test_rule_validation_reports_problems():
    assert validate_rule(SiteRule(id="ok", scope=PolicyScope.DOMAIN, pattern="example.com")) == []
    assert validate_rule(SiteRule(id="", scope=PolicyScope.DOMAIN, pattern="localhost"))
    assert validate_rule(SiteRule(id="x", scope=PolicyScope.ORIGIN, pattern="example.com"))
