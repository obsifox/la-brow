"""Browser shell model covering tabs, navigation, private browsing and recovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone as timezone_module
from enum import Enum

DEFAULT_NEW_TAB_URL = "about:newtab"
HISTORY_LIMIT = 200
MAX_TABS = 512


class SessionMode(str, Enum):
    NORMAL = "normal"
    PRIVATE = "private"


class PermissionKind(str, Enum):
    GEOLOCATION = "geolocation"
    NOTIFICATIONS = "notifications"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    CLIPBOARD = "clipboard"
    STORAGE = "storage"


PERMISSION_DEFAULTS = {
    PermissionKind.GEOLOCATION: "prompt",
    PermissionKind.NOTIFICATIONS: "prompt",
    PermissionKind.CAMERA: "prompt",
    PermissionKind.MICROPHONE: "prompt",
    PermissionKind.CLIPBOARD: "prompt",
    PermissionKind.STORAGE: "allow",
}


@dataclass
class Tab:
    tab_id: int
    url: str = DEFAULT_NEW_TAB_URL
    title: str = ""
    history: list[str] = field(default_factory=list)
    history_index: int = -1
    crashed: bool = False

    def __post_init__(self) -> None:
        if not self.history:
            self.history = [self.url]
            self.history_index = 0

    def navigate(self, url: str) -> str:
        self.history = self.history[: self.history_index + 1]
        self.history.append(url)
        self.history = self.history[-HISTORY_LIMIT:]
        self.history_index = len(self.history) - 1
        self.url = url
        return self.url

    def can_go_back(self) -> bool:
        return self.history_index > 0

    def can_go_forward(self) -> bool:
        return self.history_index < len(self.history) - 1

    def back(self) -> str:
        if self.can_go_back():
            self.history_index -= 1
            self.url = self.history[self.history_index]
        return self.url

    def forward(self) -> str:
        if self.can_go_forward():
            self.history_index += 1
            self.url = self.history[self.history_index]
        return self.url

    def reload(self) -> str:
        return self.url

    def stop(self) -> None:
        return None

    def mark_crashed(self) -> None:
        self.crashed = True

    def recover(self) -> dict:
        self.crashed = False
        return {"tab_id": self.tab_id, "url": self.url, "recovered_at": utc_now()}

    def as_dict(self) -> dict:
        return {
            "tab_id": self.tab_id,
            "url": self.url,
            "title": self.title,
            "history_length": len(self.history),
            "history_index": self.history_index,
            "crashed": self.crashed,
        }


def utc_now() -> str:
    return datetime.now(timezone_module.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class BrowserShell:
    """Minimal, testable shell independent from the environment subsystem."""

    def __init__(self, session_mode: SessionMode = SessionMode.NORMAL) -> None:
        self.session_mode = session_mode
        self.tabs: dict[int, Tab] = {}
        self.active_tab_id: int | None = None
        self.next_tab_id = 1
        self.permission_overrides: dict[str, str] = {}
        self.downloads: list[dict] = []
        self.bookmarks: list[dict] = []
        self.history: list[dict] = []

    def open_tab(self, url: str = DEFAULT_NEW_TAB_URL) -> Tab:
        if len(self.tabs) >= MAX_TABS:
            raise RuntimeError("tab limit reached")
        tab = Tab(tab_id=self.next_tab_id, url=url)
        tab.navigate(url)
        self.tabs[tab.tab_id] = tab
        self.next_tab_id += 1
        self.active_tab_id = tab.tab_id
        if self.session_mode is SessionMode.NORMAL:
            self.history.append({"url": url, "visited_at": utc_now()})
        return tab

    def close_tab(self, tab_id: int) -> None:
        self.tabs.pop(tab_id, None)
        if self.active_tab_id == tab_id:
            self.active_tab_id = next(iter(self.tabs), None)

    def active_tab(self) -> Tab | None:
        if self.active_tab_id is None:
            return None
        return self.tabs.get(self.active_tab_id)

    def navigate(self, url: str) -> None:
        tab = self.active_tab() or self.open_tab(url)
        tab.navigate(url)
        if self.session_mode is SessionMode.NORMAL:
            self.history.append({"url": url, "visited_at": utc_now()})

    def add_bookmark(self, url: str, title: str) -> dict:
        entry = {"url": url, "title": title, "created_at": utc_now()}
        self.bookmarks.append(entry)
        return entry

    def record_download(self, url: str, path: str, size_bytes: int) -> dict:
        entry = {"url": url, "path": path, "size_bytes": size_bytes, "completed_at": utc_now()}
        self.downloads.append(entry)
        return entry

    def set_permission(self, kind: PermissionKind, value: str) -> dict:
        if value not in {"allow", "deny", "prompt"}:
            raise ValueError("permission value must be allow, deny or prompt")
        self.permission_overrides[kind.value] = value
        return {"kind": kind.value, "value": value}

    def effective_permission(self, kind: PermissionKind) -> str:
        return self.permission_overrides.get(kind.value, PERMISSION_DEFAULTS[kind])

    def session_snapshot(self) -> dict:
        return {
            "session_mode": self.session_mode.value,
            "active_tab_id": self.active_tab_id,
            "tabs": [tab.as_dict() for tab in self.tabs.values()],
            "captured_at": utc_now(),
        }

    def restore_session(self, snapshot: dict) -> dict:
        self.tabs = {}
        for entry in snapshot.get("tabs", []):
            tab = Tab(tab_id=entry["tab_id"], url=entry["url"])
            tab.crashed = bool(entry.get("crashed"))
            self.tabs[tab.tab_id] = tab
        self.active_tab_id = snapshot.get("active_tab_id")
        self.session_mode = SessionMode(snapshot.get("session_mode", SessionMode.NORMAL.value))
        return {"restored_tabs": len(self.tabs), "active_tab_id": self.active_tab_id}
