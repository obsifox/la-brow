"""Per site environment policy models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PolicyScope(str, Enum):
    GLOBAL = "global"
    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    ORIGIN = "origin"
    PRIVATE_BROWSING = "private_browsing"
    NORMAL_BROWSING = "normal_browsing"


SCOPE_SPECIFICITY = {
    PolicyScope.GLOBAL: 0,
    PolicyScope.NORMAL_BROWSING: 1,
    PolicyScope.PRIVATE_BROWSING: 1,
    PolicyScope.DOMAIN: 2,
    PolicyScope.SUBDOMAIN: 3,
    PolicyScope.ORIGIN: 4,
}


@dataclass
class SiteRule:
    id: str
    scope: PolicyScope
    pattern: str
    overrides: dict = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True
    description: str = ""

    def specificity(self) -> int:
        return SCOPE_SPECIFICITY[self.scope]

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "scope": self.scope.value,
            "pattern": self.pattern,
            "overrides": dict(self.overrides),
            "priority": self.priority,
            "enabled": self.enabled,
            "description": self.description,
        }


@dataclass
class PolicyResolution:
    matched_rules: list[dict] = field(default_factory=list)
    effective_overrides: dict = field(default_factory=dict)
    trace: list[dict] = field(default_factory=list)
    unmatched: bool = True

    def as_dict(self) -> dict:
        return {
            "matched_rules": self.matched_rules,
            "effective_overrides": dict(self.effective_overrides),
            "trace": list(self.trace),
            "unmatched": self.unmatched,
        }
