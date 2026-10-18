"""Read pages through the user's signed-in Arc browser (macOS, AppleScript).

No credentials are handled here: Arc already holds the user's sessions. Each call
opens its own tab, reads it, and closes it, so parallel callers don't collide.

Requires: macOS, Arc running, and Automation permission for the calling app.
"""
from __future__ import annotations

import fcntl
import subprocess
import tempfile
import time
from typing import Callable, Optional

Runner = Callable[[str], str]
_LOCK_PATH = tempfile.gettempdir() + "/arc_browser_open_tab.lock"

_LOGIN_MARKERS = ("sign in to continue", "log in to continue", "verify you are human", "just a moment")


def run_applescript(script: str, timeout: int = 60) -> str:
    """Run AppleScript via osascript and return stripped stdout; raise on failure."""
    proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "osascript failed")
    return proc.stdout.strip()


def _q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def open_tab(url: str, run: Runner = run_applescript) -> str:
    """Open url in a new Arc tab and return the tab id."""
    # Arc can't return the id of a freshly made tab directly, so read it from the
    # (just-activated) tab; a file lock keeps parallel callers from interleaving.
    with open(_LOCK_PATH, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return run(
            'tell application "Arc" to tell front window\n'
            f"make new tab with properties {{URL:{_q(url)}}}\n"
            "return id of active tab\n"
            "end tell"
        )


def tab_js(tab_id: str, js: str, run: Runner = run_applescript) -> str:
    """Execute JavaScript in the tab with the given id and return the result."""
    return run(
        f'tell application "Arc" to tell front window to tell tab id {_q(tab_id)} '
        f"to return execute javascript {_q(js)}"
    )


def close_tab(tab_id: str, run: Runner = run_applescript) -> None:
    run(f'tell application "Arc" to tell front window to tell tab id {_q(tab_id)} to close')


def looks_blocked(text: str) -> bool:
    """True when the page text looks like a login wall, CAPTCHA, or bot check."""
    head = text[:2000].lower()
    return any(marker in head for marker in _LOGIN_MARKERS)


def fetch_page_text(
    url: str,
    settle_seconds: float = 6.0,
    max_chars: int = 60000,
    run: Runner = run_applescript,
    sleep: Callable[[float], None] = time.sleep,
) -> Optional[str]:
    """Return innerText of url from a fresh Arc tab, or None if the page looks blocked.

    The tab is always closed. Callers should record None as a "gap", never bypass it.
    """
    tab_id = open_tab(url, run)
    try:
        sleep(settle_seconds)
        text = tab_js(tab_id, f"document.body.innerText.slice(0,{int(max_chars)})", run)
    finally:
        close_tab(tab_id, run)
    return None if looks_blocked(text) else text


if __name__ == "__main__":  # CLI: python -m clients.arc_browser <url>
    import sys

    out = fetch_page_text(sys.argv[1])
    print(out if out is not None else "BLOCKED: login wall, CAPTCHA, or bot check", file=sys.stdout)
