# Browser Test Matrix

| Case | Expected |
| --- | --- |
| Tab creation | Tab registered with history entry |
| Navigation | History appended, index advanced |
| Back and forward | Index movement with correct boundaries |
| Branch navigation | Forward history discarded after a new navigation |
| Tab close | Active tab selection moves to a remaining tab |
| Private browsing | History not recorded |
| Permissions | Defaults documented, overrides recorded, invalid values refused |
| Crash recovery | Crashed tab recovers with its address |
| Session snapshot | Tabs and active identifier captured |
| Session restore | Tabs and private mode restored |
| Bookmarks and downloads | Entries recorded with timestamps |
| Tab limit | Refused above the documented maximum |

Executed by `tests/unit/test_browser_shell.py`.
