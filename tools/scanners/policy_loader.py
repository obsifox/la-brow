"""Load scanner policy and exemption registry from engineering configuration."""

from __future__ import annotations

import fnmatch
from pathlib import Path

import yaml

CODE_STYLE_PATH = "config/engineering/code-style.yaml"
BRANDING_PATH = "config/engineering/branding-policy.yaml"


def load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"missing configuration file: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_code_style(repo: Path) -> dict:
    return load_yaml(repo / CODE_STYLE_PATH)


def load_branding(repo: Path) -> dict:
    return load_yaml(repo / BRANDING_PATH)


def exemptions_for(repo: Path, scanner: str) -> list[dict]:
    style = load_code_style(repo)
    selected = []
    for entry in style.get("exemptions", []):
        if scanner in entry.get("scanners", []):
            selected.append(entry)
    return selected


def is_exempt(relative_path: str, exemptions: list[dict]) -> dict | None:
    for entry in exemptions:
        for pattern in entry.get("paths", []):
            if fnmatch.fnmatch(relative_path, pattern):
                return entry
            if pattern.endswith("/**") and relative_path.startswith(pattern[:-3]):
                return entry
    return None


def iter_repository_files(repo: Path, extensions: set[str] | None = None, names: set[str] | None = None):
    for path in sorted(repo.rglob("*")):
        if not path.is_file():
            continue
        parts = set(path.relative_to(repo).parts)
        if parts & {".git", "__pycache__", ".pytest_cache", "node_modules", ".gradle"}:
            continue
        if extensions is not None and path.suffix.lower() not in extensions:
            if names is None or path.name not in names:
                continue
        yield path
