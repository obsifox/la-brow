"""Deterministic per site policy resolution."""

from __future__ import annotations

from urllib.parse import urlsplit

from policy.models import PolicyResolution, PolicyScope, SiteRule


def rule_matches(rule: SiteRule, host: str, origin: str, private_browsing: bool) -> bool:
    if not rule.enabled:
        return False
    target = host.lower()
    pattern = rule.pattern.lower()
    if rule.scope is PolicyScope.GLOBAL:
        return True
    if rule.scope is PolicyScope.PRIVATE_BROWSING:
        return private_browsing
    if rule.scope is PolicyScope.NORMAL_BROWSING:
        return not private_browsing
    if rule.scope is PolicyScope.DOMAIN:
        return target == pattern or target.endswith("." + pattern)
    if rule.scope is PolicyScope.SUBDOMAIN:
        return target.endswith("." + pattern) and target != pattern
    if rule.scope is PolicyScope.ORIGIN:
        return origin.lower() == pattern
    return False


def sort_key(rule: SiteRule) -> tuple:
    return (-rule.specificity(), -rule.priority, rule.id)


def resolve(rules: list[SiteRule], url: str, private_browsing: bool = False) -> PolicyResolution:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    origin = f"{parts.scheme}://{parts.netloc}".lower() if parts.scheme and parts.netloc else ""
    matched = [rule for rule in rules if rule_matches(rule, host, origin, private_browsing)]
    ordered = sorted(matched, key=sort_key)
    resolution = PolicyResolution(unmatched=not ordered)
    for rule in ordered:
        resolution.matched_rules.append(rule.as_dict())
    merged: dict = {}
    applied_order = list(reversed(ordered))
    for rule in applied_order:
        for key, value in rule.overrides.items():
            previous = merged.get(key)
            merged[key] = value
            resolution.trace.append(
                {
                    "field": key,
                    "value": value,
                    "rule_id": rule.id,
                    "scope": rule.scope.value,
                    "specificity": rule.specificity(),
                    "priority": rule.priority,
                    "previous_value": previous,
                    "decision": "applied" if previous is None else "replaces-lower-specificity-value",
                }
            )
    resolution.effective_overrides = merged
    resolution.trace.append(
        {
            "field": "*",
            "decision": "resolution-complete",
            "matched_rule_count": len(resolution.matched_rules),
            "precedence_order": "origin > subdomain > domain > browsing-mode > global, then priority, then rule id",
        }
    )
    return resolution


def validate_rule(rule: SiteRule) -> list[dict]:
    problems: list[dict] = []
    if not rule.id or not rule.id.strip():
        problems.append({"field": "id", "issue": "must-be-non-empty"})
    if rule.scope in {PolicyScope.DOMAIN, PolicyScope.SUBDOMAIN}:
        if "." not in rule.pattern:
            problems.append({"field": "pattern", "issue": "domain-scope-requires-a-registrable-domain"})
        if any(character in rule.pattern for character in ("/", ":", "*")):
            problems.append({"field": "pattern", "issue": "domain-pattern-must-not-contain-wildcards-or-paths"})
    if rule.scope is PolicyScope.ORIGIN:
        parts = urlsplit(rule.pattern)
        if not parts.scheme or not parts.netloc:
            problems.append({"field": "pattern", "issue": "origin-scope-requires-scheme-and-host"})
    if not isinstance(rule.overrides, dict):
        problems.append({"field": "overrides", "issue": "must-be-a-mapping"})
    return problems
