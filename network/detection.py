"""Network environment detection with explicit confidence reporting."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

RESOLV_CONF = Path("/etc/resolv.conf")
VPN_INTERFACE_HINTS = ("tun", "tap", "wg", "ppp", "utun", "nordlynx", "ipsec", "zerotier", "tailscale")


@dataclass(frozen=True)
class NetworkInterface:
    name: str
    addresses: tuple[str, ...]
    flags: tuple[str, ...]

    def as_dict(self) -> dict:
        return {"name": self.name, "addresses": list(self.addresses), "flags": list(self.flags)}


@dataclass
class DetectionSignals:
    interfaces: list[NetworkInterface] = field(default_factory=list)
    default_route_interface: str | None = None
    proxy_environment: dict = field(default_factory=dict)
    resolver_addresses: list[str] = field(default_factory=list)
    vpn_interface_detected: str | None = None
    hostname: str | None = None
    reachability: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "interfaces": [interface.as_dict() for interface in self.interfaces],
            "default_route_interface": self.default_route_interface,
            "proxy_environment": dict(self.proxy_environment),
            "resolver_addresses": list(self.resolver_addresses),
            "vpn_interface_detected": self.vpn_interface_detected,
            "hostname": self.hostname,
            "reachability": dict(self.reachability),
        }


def read_interfaces() -> list[NetworkInterface]:
    results: list[NetworkInterface] = []
    try:
        output = subprocess.run(
            ["ip", "-o", "addr", "show"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        output = None
    if output is not None and output.returncode == 0:
        grouped: dict[str, list[str]] = {}
        flags: dict[str, list[str]] = {}
        for line in output.stdout.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            name = parts[1]
            state_flags = parts[2]
            address = parts[3]
            grouped.setdefault(name, []).append(address)
            flags[name] = [state_flags]
        for name, addresses in grouped.items():
            results.append(NetworkInterface(name=name, addresses=tuple(addresses), flags=tuple(flags.get(name, []))))
    if results:
        return results
    for name in sorted(os.listdir("/sys/class/net")):
        hardware_address = ""
        address_path = Path(f"/sys/class/net/{name}/address")
        if address_path.is_file():
            try:
                hardware_address = address_path.read_text(encoding="utf-8").strip()
            except OSError:
                hardware_address = ""
        results.append(
            NetworkInterface(
                name=name,
                addresses=(),
                flags=(f"hardware_address={hardware_address}",) if hardware_address else (),
            )
        )
    return results


def read_default_route() -> str | None:
    route_path = Path("/proc/net/route")
    if not route_path.is_file():
        return None
    try:
        lines = route_path.read_text(encoding="utf-8").splitlines()[1:]
    except OSError:
        return None
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "00000000":
            return parts[0]
    return None


def read_resolvers() -> list[str]:
    addresses: list[str] = []
    if not RESOLV_CONF.is_file():
        return addresses
    try:
        content = RESOLV_CONF.read_text(encoding="utf-8")
    except OSError:
        return addresses
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("nameserver"):
            parts = stripped.split()
            if len(parts) >= 2:
                addresses.append(parts[1])
    return addresses


def read_proxy_environment() -> dict:
    keys = ("http_proxy", "https_proxy", "all_proxy", "no_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")
    return {key: os.environ[key] for key in keys if key in os.environ}


def detect_vpn(interfaces: list[NetworkInterface]) -> str | None:
    for interface in interfaces:
        lowered = interface.name.lower()
        if any(lowered.startswith(hint) for hint in VPN_INTERFACE_HINTS):
            return interface.name
    if shutil.which("nmcli"):
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "TYPE,STATE,NAME", "connection", "show", "--active"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except subprocess.SubprocessError:
            return None
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "vpn" in line.lower() or "wireguard" in line.lower():
                    return line.split(":")[-1] or "vpn"
    return None


def probe_reachability(timeout: float = 1.5) -> dict:
    results = {}
    for label, target in (("dns_udp", ("1.1.1.1", 53)), ("https", ("1.1.1.1", 443)), ("dot", ("1.1.1.1", 853))):
        socket_handle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_handle.settimeout(timeout)
        try:
            socket_handle.connect(target)
            results[label] = True
        except OSError:
            results[label] = False
        finally:
            socket_handle.close()
    return results


def detect_environment(probe_network: bool = False) -> DetectionSignals:
    interfaces = read_interfaces()
    signals = DetectionSignals(
        interfaces=interfaces,
        default_route_interface=read_default_route(),
        proxy_environment=read_proxy_environment(),
        resolver_addresses=read_resolvers(),
        vpn_interface_detected=detect_vpn(interfaces),
        hostname=socket.gethostname(),
    )
    if probe_network:
        signals.reachability = probe_reachability()
    return signals


def signal_confidence(signals: DetectionSignals) -> tuple[float, list[str]]:
    score = 0.0
    notes: list[str] = []
    if signals.interfaces:
        score += 0.15
        notes.append("interfaces-detected")
    if signals.default_route_interface:
        score += 0.2
        notes.append("default-route-detected")
    if signals.resolver_addresses:
        score += 0.1
        notes.append("resolvers-detected")
    if signals.vpn_interface_detected:
        score += 0.15
        notes.append("vpn-interface-detected")
    if signals.proxy_environment:
        score += 0.1
        notes.append("proxy-environment-detected")
    notes.append("no-network-geolocation-service-configured")
    return min(score, 1.0), notes
