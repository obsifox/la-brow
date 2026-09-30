"""Detect non-English scripts in repository content."""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

REPO_ROOT_GUESS = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_GUESS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_GUESS))

from tools.scanners.policy_loader import exemptions_for, is_exempt, iter_repository_files

FORBIDDEN_SCRIPT_RANGES = [
    (0x0400, 0x04FF, "cyrillic"),
    (0x0500, 0x052F, "cyrillic-supplement"),
    (0x0530, 0x058F, "armenian"),
    (0x0590, 0x05FF, "hebrew"),
    (0x0600, 0x06FF, "arabic"),
    (0x0700, 0x074F, "syriac"),
    (0x0750, 0x077F, "arabic-supplement"),
    (0x0900, 0x097F, "devanagari"),
    (0x0E00, 0x0E7F, "thai"),
    (0x3040, 0x30FF, "japanese"),
    (0x3400, 0x4DBF, "cjk-extension"),
    (0x4E00, 0x9FFF, "cjk-unified"),
    (0xAC00, 0xD7AF, "hangul"),
    (0xFB50, 0xFDFF, "arabic-presentation-a"),
    (0xFE70, 0xFEFF, "arabic-presentation-b"),
    (0x0F00, 0x0FFF, "tibetan"),
    (0x10A0, 0x10FF, "georgian"),
]

ALLOWED_PUNCTUATION = {
    0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2026, 0x2022, 0x00B7,
    0x2039, 0x203A, 0x00A0, 0x2192, 0x2190, 0x2500, 0x2502, 0x2514, 0x251C,
    0x00AB, 0x00BB, 0x00E9, 0x00FC, 0x00F6, 0x00E4, 0x00DF, 0x00E0, 0x00E7,
    0x00EE, 0x00F4, 0x00FB, 0x00E1, 0x00ED, 0x00F3, 0x00FA, 0x00F1,
}

TEXT_EXTENSIONS = {
    ".py", ".kt", ".kts", ".java", ".js", ".ts", ".sh", ".yaml", ".yml", ".json",
    ".toml", ".xml", ".svg", ".html", ".css", ".md", ".txt", ".gradle", ".pro",
    ".properties", ".ini", ".cfg", ".csv",
}

TEXT_NAMES = {"Makefile", "Dockerfile", "NOTICE"}


def scan_text(text: str, max_findings: int = 40) -> list[dict]:
    findings: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for column, character in enumerate(line, start=1):
            code_point = ord(character)
            if code_point < 128 or code_point in ALLOWED_PUNCTUATION:
                continue
            category = unicodedata.category(character)
            if category in {"Mn", "Me"}:
                continue
            for start, end, script in FORBIDDEN_SCRIPT_RANGES:
                if start <= code_point <= end:
                    findings.append(
                        {
                            "line": line_number,
                            "column": column,
                            "code_point": f"U+{code_point:04X}",
                            "script": script,
                        }
                    )
                    break
            if len(findings) >= max_findings:
                return findings
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository for non-English scripts")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json-out")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    exemptions = exemptions_for(repo, "language")
    report = {"scanner": "english", "repo": str(repo), "violations": [], "exempted_files": []}
    for path in iter_repository_files(repo, TEXT_EXTENSIONS, TEXT_NAMES):
        relative = path.relative_to(repo).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        findings = scan_text(text)
        if not findings:
            continue
        exemption = is_exempt(relative, exemptions)
        if exemption:
            report["exempted_files"].append({"path": relative, "exemption": exemption["id"], "count": len(findings)})
            continue
        report["violations"].append({"path": relative, "findings": findings})
    report["violation_count"] = sum(len(item["findings"]) for item in report["violations"])
    report["status"] = "FAIL" if report["violations"] else "PASS"
    if arguments.json_out:
        Path(arguments.json_out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"english_scan status={report['status']} violations={report['violation_count']} exempted_files={len(report['exempted_files'])}")
    for item in report["violations"][:10]:
        print(f"  {item['path']}: {item['findings'][:3]}")
    return 1 if report["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
