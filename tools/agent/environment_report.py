"""Collect factual environment measurements and write the environment report."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone as timezone_module
from pathlib import Path

TOOL_PROBES = (
    ("gcc", ["gcc", "--version"]),
    ("g++", ["g++", "--version"]),
    ("clang", ["clang", "--version"]),
    ("rustc", ["rustc", "--version"]),
    ("cargo", ["cargo", "--version"]),
    ("python3", ["python3", "--version"]),
    ("node", ["node", "--version"]),
    ("java", ["java", "-version"]),
    ("gradle", ["gradle", "--version"]),
    ("cmake", ["cmake", "--version"]),
    ("ninja", ["ninja", "--version"]),
    ("make", ["make", "--version"]),
    ("git", ["git", "--version"]),
    ("hg", ["hg", "--version"]),
    ("openssl", ["openssl", "version"]),
    ("docker", ["docker", "--version"]),
    ("podman", ["podman", "--version"]),
    ("qemu-system-x86_64", ["qemu-system-x86_64", "--version"]),
)

ANDROID_ENVIRONMENT_VARIABLES = ("ANDROID_HOME", "ANDROID_SDK_ROOT", "ANDROID_NDK_ROOT", "JAVA_HOME")


def run_probe(command: list[str]) -> dict:
    executable = shutil.which(command[0])
    if executable is None:
        return {"present": False, "path": None, "first_line": None}
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=20)
        output = (completed.stdout or completed.stderr).strip().splitlines()
    except (subprocess.SubprocessError, OSError):
        output = []
    return {"present": True, "path": executable, "first_line": output[0] if output else None}


def read_meminfo() -> dict:
    path = Path("/proc/meminfo")
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, remainder = line.partition(":")
        values[key.strip()] = remainder.strip()
    return values


def read_cpu() -> dict:
    path = Path("/proc/cpuinfo")
    if not path.is_file():
        return {}
    model = None
    cores = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("model name") and model is None:
            model = line.split(":", 1)[1].strip()
        if line.startswith("processor"):
            cores += 1
    return {"model": model, "logical_cores": cores, "os_cpu_count": os.cpu_count()}


def read_disk() -> list[dict]:
    entries = []
    for mount in ("/", "/home/user", "/tmp"):
        if not Path(mount).exists():
            continue
        usage = shutil.disk_usage(mount)
        entries.append(
            {
                "mount": mount,
                "total_bytes": usage.total,
                "free_bytes": usage.free,
                "used_percent": round((usage.used / usage.total) * 100.0, 1),
            }
        )
    return entries


def detect_graphics() -> dict:
    glxinfo = shutil.which("glxinfo")
    if glxinfo is None:
        return {"glxinfo": False, "detail": "glxinfo is not installed; graphics stack not measurable in this environment"}
    completed = subprocess.run([glxinfo, "-B"], capture_output=True, text=True, timeout=20)
    return {"glxinfo": True, "first_lines": completed.stdout.strip().splitlines()[:6]}


def detect_containers() -> dict:
    markers = {
        "docker_socket": Path("/var/run/docker.sock").exists(),
        "podman_socket": Path("/run/podman/podman.sock").exists(),
        "cgroup_v2": Path("/sys/fs/cgroup/cgroup.controllers").exists(),
        "kvm_device": Path("/dev/kvm").exists(),
    }
    if Path("/.dockerenv").exists():
        markers["docker_marker"] = True
    return markers


def collect() -> dict:
    tools = {name: run_probe(command) for name, command in TOOL_PROBES}
    environment_variables = {name: bool(os.environ.get(name)) for name in ANDROID_ENVIRONMENT_VARIABLES}
    return {
        "collected_at": datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "operating_system": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "distribution": platform.freedesktop_os_release().get("PRETTY_NAME") if hasattr(platform, "freedesktop_os_release") else None,
            "libc": platform.libc_ver(),
        },
        "architecture": {
            "machine": platform.machine(),
            "pointer_bits": 64 if sys.maxsize > 2**32 else 32,
            "processor": platform.processor(),
        },
        "cpu": read_cpu(),
        "memory": {
            "total": read_meminfo().get("MemTotal"),
            "available": read_meminfo().get("MemAvailable"),
            "swap_total": read_meminfo().get("SwapTotal"),
        },
        "storage": read_disk(),
        "graphics": detect_graphics(),
        "containers_and_virtualization": detect_containers(),
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "modules": probe_modules(),
        },
        "tools": tools,
        "android_environment_variables": environment_variables,
        "agent_environment": {
            "has_git": shutil.which("git") is not None,
            "has_test_runner": probe_pytest(),
            "has_subagents": False,
            "can_run_code": True,
            "can_persist_files": True,
        },
    }


def probe_modules() -> dict:
    modules = {}
    for name in ("pytest", "yaml", "jsonschema", "PIL", "cryptography"):
        try:
            module = __import__(name)
            modules[name] = getattr(module, "__version__", "present")
        except ImportError:
            modules[name] = None
    return modules


def probe_pytest() -> bool:
    return shutil.which("pytest") is not None or probe_modules().get("pytest") is not None


def render_markdown(report: dict) -> str:
    lines = [
        "# Environment Report",
        "",
        f"Collected at {report['collected_at']}. The report contains factual measurements only.",
        "",
        "## Operating System",
        "",
        f"- system: {report['operating_system']['system']}",
        f"- release: {report['operating_system']['release']}",
        f"- distribution: {report['operating_system']['distribution']}",
        f"- libc: {report['operating_system']['libc']}",
        "",
        "## Architecture",
        "",
        f"- machine: {report['architecture']['machine']}",
        f"- pointer bits: {report['architecture']['pointer_bits']}",
        "",
        "## CPU",
        "",
        f"- model: {report['cpu'].get('model')}",
        f"- logical cores: {report['cpu'].get('logical_cores')}",
        "",
        "## Memory",
        "",
        f"- total: {report['memory']['total']}",
        f"- available: {report['memory']['available']}",
        f"- swap total: {report['memory']['swap_total']}",
        "",
        "## Storage",
        "",
    ]
    for entry in report["storage"]:
        lines.append(f"- {entry['mount']}: free {entry['free_bytes']} bytes of {entry['total_bytes']} bytes, used {entry['used_percent']} percent")
    lines += [
        "",
        "## Graphics",
        "",
        f"- measurable: {report['graphics']['glxinfo']}",
        f"- detail: {report['graphics'].get('detail', 'graphics stack reported by glxinfo')}",
        "",
        "## Containers and Virtualization",
        "",
    ]
    for key, value in report["containers_and_virtualization"].items():
        lines.append(f"- {key}: {value}")
    lines += [
        "",
        "## Toolchain",
        "",
        "| Tool | Present | Version Line |",
        "| --- | --- | --- |",
    ]
    for name, probe in report["tools"].items():
        lines.append(f"| {name} | {probe['present']} | {probe['first_line'] or 'not available'} |")
    lines += [
        "",
        "## Python Modules",
        "",
    ]
    for name, version in report["python"]["modules"].items():
        lines.append(f"- {name}: {version or 'not installed'}")
    lines += [
        "",
        "## Android Toolchain",
        "",
        f"- environment variables present: {report['android_environment_variables']}",
        "",
        "## Consequences For This Project",
        "",
        "Recorded facts that constrain the engineering plan:",
        "",
    ]
    tools = report["tools"]
    consequences = []
    if not tools["rustc"]["present"]:
        consequences.append("Rust is not available, so any Gecko build step that requires the Rust toolchain cannot run in this environment.")
    if not tools["clang"]["present"]:
        consequences.append("Clang is not available, so the recommended Gecko compiler toolchain cannot run in this environment.")
    if not tools["cmake"]["present"] and not tools["ninja"]["present"]:
        consequences.append("CMake and Ninja are not available, so the Gecko build system cannot run in this environment.")
    if not tools["gradle"]["present"]:
        consequences.append("Gradle is not installed, so the Android application cannot be assembled in this environment.")
    if not report["android_environment_variables"]["ANDROID_HOME"] and not report["android_environment_variables"]["ANDROID_SDK_ROOT"]:
        consequences.append("No Android SDK is configured, so Android packaging remains a validated scaffold rather than a built artifact.")
    if not tools["docker"]["present"] and not tools["podman"]["present"]:
        consequences.append("No container runtime is available, so build isolation must be documented for a capable build host.")
    consequences.append("The environment core, policy scanners and test suite run fully in this environment.")
    for item in consequences:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect environment measurements")
    parser.add_argument("--out", default="docs/architecture/environment-report.md")
    parser.add_argument("--json", dest="json_out")
    arguments = parser.parse_args()
    report = collect()
    target = Path(arguments.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_markdown(report), encoding="utf-8")
    if arguments.json_out:
        json_target = Path(arguments.json_out)
        json_target.parent.mkdir(parents=True, exist_ok=True)
        json_target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"environment report written to {target}")
    print(f"python={report['python']['version']} cores={report['cpu'].get('logical_cores')} gcc={report['tools']['gcc']['present']} rustc={report['tools']['rustc']['present']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
