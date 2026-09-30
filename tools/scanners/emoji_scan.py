"""Detect emoji characters in repository content."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT_GUESS = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_GUESS) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_GUESS))

from tools.scanners.policy_loader import exemptions_for, is_exempt, iter_repository_files

FORBIDDEN_RANGES = [
    (0x1F000, 0x1FAFF, "pictographs-supplement"),
    (0x1F1E6, 0x1F1FF, "regional-indicators"),
    (0x2600, 0x27BF, "misc-symbols-and-dingbats"),
    (0x2B00, 0x2BFF, "misc-symbols-and-arrows"),
    (0x2190, 0x21FF, "arrows"),
    (0xFE0F, 0xFE0F, "variation-selector-16"),
    (0x200D, 0x200D, "zero-width-joiner"),
    (0x20E3, 0x20E3, "combining-enclosing-keycap"),
    (0x3030, 0x3030, "wavy-dash"),
    (0x303D, 0x303D, "part-alternation-mark"),
    (0x00A9, 0x00A9, "copyright-sign"),
    (0x00AE, 0x00AE, "registered-sign"),
    (0x2122, 0x2122, "trade-mark-sign"),
]

TEXT_EXTENSIONS = {
    ".py", ".kt", ".kts", ".java", ".js", ".ts", ".tsx", ".jsx", ".sh", ".bash",
    ".yaml", ".yml", ".json", ".toml", ".xml", ".svg", ".html", ".css", ".md",
    ".txt", ".gradle", ".pro", ".properties", ".xmlj", ".csv", ".ini", ".cfg", ".config",
}

TEXT_NAMES = {"Makefile", "Dockerfile", "NOTICE"}

ALLOWED_SYMBOLS = {0x00A9, 0x00AE, 0x2122}


def scan_text(text: str, max_findings: int = 25) -> list[dict]:
    findings: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for column, character in enumerate(line, start=1):
            code_point = ord(character)
            if code_point in ALLOWED_SYMBOLS:
                continue
            for start, end, category in FORBIDDEN_RANGES:
                if start <= code_point <= end:
                    findings.append(
                        {
                            "line": line_number,
                            "column": column,
                            "code_point": f"U+{code_point:04X}",
                            "category": category,
                        }
                    )
                    break
            if len(findings) >= max_findings:
                return findings
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository for emoji characters")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json-out")
    arguments = parser.parse_args()
    repo = Path(arguments.repo).resolve()
    exemptions = exemptions_for(repo, "emoji")
    report = {"scanner": "emoji", "repo": str(repo), "violations": [], "exempted_files": []}
    for path in iter_repository_files(repo, TEXT_EXTENSIONS, TEXT_NAMES):
        relative = path.relative_to(repo).as_posix()
        exemption = is_exempt(relative, exemptions)
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        findings = scan_text(text)
        if findings and exemption:
            report["exempted_files"].append({"path": relative, "exemption": exemption["id"], "count": len(findings)})
            continue
        if findings:
            report["violations"].append({"path": relative, "findings": findings})
    report["status"] = "FAIL" if report["violations"] else "PASS"
    report["violation_count"] = sum(len(item["findings"]) for item in report["violations"])
    if arguments.json_out:
        Path(arguments.json_out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"emoji_scan status={report['status']} violations={report['violation_count']} exempted_files={len(report['exempted_files'])}")
    for item in report["violations"][:10]:
        print(f"  {item['path']}: {len(item['findings'])} finding(s) first={item['findings'][0]}")
    return 1 if report["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
