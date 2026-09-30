"""Generate the integrity manifest for the vendored engineering skill."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXCLUDED_DIRECTORIES = {".git", "__pycache__", ".pytest_cache"}


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRECTORIES for part in path.parts):
            continue
        yield path


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_manifest(skill_root: Path) -> tuple[list[str], str]:
    lines: list[str] = []
    aggregate = hashlib.sha256()
    for path in iter_files(skill_root):
        relative = path.relative_to(skill_root).as_posix()
        file_hash = digest(path)
        lines.append(f"{file_hash}  {relative}")
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\x00")
        aggregate.update(file_hash.encode("utf-8"))
        aggregate.update(b"\n")
    return lines, aggregate.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate integrity manifest for a vendored tree")
    parser.add_argument("--root", required=True, help="directory to hash")
    parser.add_argument("--out", required=True, help="manifest output path")
    parser.add_argument("--json", action="store_true", help="emit machine readable summary")
    arguments = parser.parse_args()
    root = Path(arguments.root)
    if not root.is_dir():
        raise SystemExit(f"missing directory: {root}")
    lines, tree_hash = build_manifest(root)
    out_path = Path(arguments.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {"root": str(root), "files": len(lines), "tree_sha256": tree_hash, "manifest": str(out_path)}
    if arguments.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"files={summary['files']} tree_sha256={tree_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
