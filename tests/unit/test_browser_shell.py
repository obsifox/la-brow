"""Browser shell navigation, privacy and recovery tests."""

from __future__ import annotations

from browser.shell import BrowserShell, PermissionKind, SessionMode, Tab


def test_navigation_history_and_back_forward():
    tab = Tab(tab_id=1, url="https://one.test")
    tab.navigate("https://two.test")
    tab.navigate("https://three.test")
    assert tab.can_go_back() is True
    assert tab.back() == "https://two.test"
    assert tab.forward() == "https://three.test"
    assert tab.back() == "https://two.test"
    tab.navigate("https://four.test")
    assert tab.can_go_forward() is False


def test_tab_opening_closing_and_active_tracking():
    shell = BrowserShell()
    first = shell.open_tab("https://one.test")
    second = shell.open_tab("https://two.test")
    assert shell.active_tab_id == second.tab_id
    shell.close_tab(second.tab_id)
    assert shell.active_tab_id == first.tab_id
    shell.close_tab(first.tab_id)
    assert shell.active_tab_id is None


def test_private_session_is_not_recorded_in_history():
    shell = BrowserShell(session_mode=SessionMode.PRIVATE)
    shell.open_tab("https://private.test")
    shell.navigate("https://private.test/other")
    assert shell.history == []


def test_normal_session_records_history():
    shell = BrowserShell()
    shell.open_tab("https://public.test")
    assert shell.history[0]["url"] == "https://public.test"


def test_permissions_default_to_prompt_and_can_be_overridden():
    shell = BrowserShell()
    assert shell.effective_permission(PermissionKind.GEOLOCATION) == "prompt"
    assert shell.effective_permission(PermissionKind.STORAGE) == "allow"
    shell.set_permission(PermissionKind.GEOLOCATION, "deny")
    assert shell.effective_permission(PermissionKind.GEOLOCATION) == "deny"


def test_invalid_permission_value_is_rejected():
    shell = BrowserShell()
    try:
        shell.set_permission(PermissionKind.CAMERA, "maybe")
    except ValueError as error:
        assert "allow, deny or prompt" in str(error)
    else:
        raise AssertionError("invalid permission value must raise")


def test_crash_recovery_keeps_url():
    tab = Tab(tab_id=3, url="https://crash.test")
    tab.mark_crashed()
    assert tab.as_dict()["crashed"] is True
    recovered = tab.recover()
    assert recovered["url"] == "https://crash.test"
    assert tab.crashed is False


def test_session_snapshot_and_restore():
    shell = BrowserShell()
    shell.open_tab("https://one.test")
    shell.open_tab("https://two.test")
    snapshot = shell.session_snapshot()
    restored = BrowserShell()
    outcome = restored.restore_session(snapshot)
    assert outcome["restored_tabs"] == 2
    assert set(restored.tabs) == set(shell.tabs)


def test_downloads_and_bookmarks_are_recorded():
    shell = BrowserShell()
    shell.add_bookmark("https://example.com", "Example")
    shell.record_download("https://example.com/file.zip", "/tmp/file.zip", 1024)
    assert shell.bookmarks[0]["title"] == "Example"
    assert shell.downloads[0]["size_bytes"] == 1024
