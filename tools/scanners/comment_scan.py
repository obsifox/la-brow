"""Detect forbidden source comments across the repository."""
from __future__ import annotations

import argparse
import json
import sys
import io
import tokenize
from pathlib import Path

REPO_ROOT_GUESS = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_GUESS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_GUESS))

from tools.scanners.policy_loader import exemptions_for, is_exempt, iter_repository_files

SLASH = chr(47)
STAR = chr(42)
HASH = chr(35)
BANG = chr(33)
ANGLE_OPEN = chr(60)
EXCLAMATION_ANGLE_OPEN = chr(60) + chr(33)
LINE_MARKER = SLASH * 2
BLOCK_OPEN = SLASH + STAR
BLOCK_CLOSE = STAR + SLASH
XML_COMMENT_OPEN = chr(60) + chr(33) + chr(45) + chr(45)
SCHEME_MARKER = chr(58) + SLASH * 2

SLASH_FAMILY = {
    ".py": "python",
    ".kt": "generic-slash",
    ".kts": "generic-slash",
    ".java": "generic-slash",
    ".js": "generic-slash",
    ".ts": "generic-slash",
    ".tsx": "generic-slash",
    ".jsx": "generic-slash",
    ".gradle": "generic-slash",
    ".pro": "generic-slash",
    ".css": "generic-slash",
}
HASH_FAMILY = {
    ".sh": "generic-hash",
    ".bash": "generic-hash",
    ".yaml": "generic-hash",
    ".yml": "generic-hash",
    ".toml": "generic-hash",
    ".properties": "generic-hash",
    ".ini": "generic-hash",
    ".cfg": "generic-hash",
}
XML_FAMILY = {".xml": "xml", ".svg": "xml", ".html": "xml", ".xhtml": "xml"}
NAMED_FILES = {"Makefile": "generic-hash", "Dockerfile": "generic-hash"}


def classify(path: Path) -> str | None:
    if path.name in NAMED_FILES:
        return NAMED_FILES[path.name]
    return SLASH_FAMILY.get(path.suffix.lower()) or HASH_FAMILY.get(path.suffix.lower()) or XML_FAMILY.get(path.suffix.lower())


def python_comment_findings(text: str) -> list[dict]:
    findings: list[dict] = []
    reader = io.StringIO(text).readline
    try:
        for token in tokenize.generate_tokens(reader):
            if token.type == tokenize.COMMENT:
                findings.append({"line": token.start[0], "column": token.start[1] + 1, "token": "line-comment"})
            if token.type == tokenize.STRING:
                pass
    except (tokenize.TokenError, IndentationError, SyntaxError):
        findings.append({"line": 0, "column": 0, "token": "tokenizer-error-requires-manual-review"})
    return findings


def block_token_findings(text: str, family: str) -> list[dict]:
    findings: list[dict] = []
    in_block = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        masked = mask_strings(line, family)
        index = 0
        while index < len(masked):
            if not in_block and masked.startswith(BLOCK_OPEN, index):
                findings.append({"line": line_number, "column": index + 1, "token": "block-comment-open"})
                in_block = True
                index += 2
                continue
            if in_block and masked.startswith(BLOCK_CLOSE, index):
                findings.append({"line": line_number, "column": index + 1, "token": "block-comment-close"})
                in_block = False
                index += 2
                continue
            index += 1
    if in_block:
        findings.append({"line": len(text.splitlines()), "column": 1, "token": "block-comment-unterminated"})
    return findings


def mask_strings(line: str, family: str) -> str:
    characters = list(line)
    quote = None
    index = 0
    while index < len(characters):
        character = characters[index]
        if quote:
            if character == "\\" and family == "python":
                if index + 1 < len(characters):
                    characters[index] = " "
                    characters[index + 1] = " "
                index += 2
                continue
            if character == quote:
                quote = None
            else:
                characters[index] = " "
            index += 1
            continue
        if family in {"python", "generic-slash"} and character in {'"', "'"}:
            quote = character
            characters[index] = " "
            index += 1
            continue
        if family == "generic-hash" and character in {'"', "'"}:
            quote = character
            characters[index] = " "
            index += 1
            continue
        index += 1
    masked = "".join(characters)
    return masked.replace(SCHEME_MARKER, " " * len(SCHEME_MARKER))


def slash_findings(text: str, family: str) -> list[dict]:
    findings: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        masked = mask_strings(line, family)
        index = 0
        while index < len(masked) - 1:
            if masked.startswith(LINE_MARKER, index):
                findings.append({"line": line_number, "column": index + 1, "token": "line-comment-double-slash"})
                break
            index += 1
    return findings


def hash_findings(text: str, path: Path) -> list[dict]:
    findings: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(HASH + BANG) and line_number == 1:
            continue
        masked = mask_strings(line, "generic-hash")
        position = masked.find(HASH)
        if position == -1:
            continue
        prefix = masked[:position]
        if prefix.strip() == "" or prefix.rstrip().endswith(("=", ":", "-")):
            findings.append({"line": line_number, "column": position + 1, "token": "hash-comment"})
    return findings


def xml_findings(text: str) -> list[dict]:
    findings: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        position = line.find(XML_COMMENT_OPEN)
        if position != -1:
            findings.append({"line": line_number, "column": position + 1, "token": "xml-comment"})
    return findings


def scan_file(path: Path, family: str) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    if family == "python":
        return python_comment_findings(text)
    if family == "xml":
        return xml_findings(text)
    if family == "generic-hash":
        return hash_findings(text, path)
    return slash_findings(text, family) + block_token_findings(text, family)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan source files for forbidden comments")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json-out")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    exemptions = exemptions_for(repo, "comment")
    extensions = set(SLASH_FAMILY) | set(HASH_FAMILY) | set(XML_FAMILY)
    report = {"scanner": "comment", "repo": str(repo), "violations": [], "exempted_files": [], "scanned_files": 0}
    for path in iter_repository_files(repo, extensions, set(NAMED_FILES)):
        relative = path.relative_to(repo).as_posix()
        family = classify(path)
        if family is None:
            continue
        report["scanned_files"] += 1
        findings = scan_file(path, family)
        if not findings:
            continue
        exemption = is_exempt(relative, exemptions)
        if exemption:
            report["exempted_files"].append({"path": relative, "exemption": exemption["id"], "count": len(findings)})
            continue
        report["violations"].append({"path": relative, "family": family, "findings": findings})
    report["violation_count"] = sum(len(item["findings"]) for item in report["violations"])
    report["status"] = "FAIL" if report["violations"] else "PASS"
    if arguments.json_out:
        Path(arguments.json_out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"comment_scan status={report['status']} scanned={report['scanned_files']} violations={report['violation_count']} exempted_files={len(report['exempted_files'])}")
    for item in report["violations"][:15]:
        print(f"  {item['path']}: {item['findings'][:3]}")
    return 1 if report["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
