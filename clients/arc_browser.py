"""Read pages through the user's signed-in Arc browser (macOS, AppleScript).

No credentials are handled here: Arc already holds the user's sessions. Each call
opens its own tab, reads it, and closes it, so parallel callers don't collide.

Requires: macOS, Arc running, and Automation permission for the calling app.

Pages open in a dedicated Arc window (created on first use, reused afterwards), and whichever app
was in front is brought back to the front right after, so this never takes over the user's screen.
"""
from __future__ import annotations

import contextlib
import fcntl
import os
import re
import subprocess
import tempfile
import time
from typing import Callable, Optional

Runner = Callable[[str], str]
_LOCK_PATH = tempfile.gettempdir() + "/arc_browser_open_tab.lock"
WINDOW_FILE = tempfile.gettempdir() + "/arc_browser_window.id"  # id of the dedicated automation window
KEEP_FOCUS = True  # hand focus back to the previously frontmost app after touching Arc

_LOGIN_MARKERS = ("sign in to continue", "log in to continue", "verify you are human", "just a moment")


def run_applescript(script: str, timeout: int = 60) -> str:
    """Run AppleScript via osascript and return stripped stdout; raise on failure."""
    proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "osascript failed")
    return proc.stdout.strip()


def _q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _front_app() -> Optional[str]:
    """Name of the frontmost macOS app (via lsappinfo, no permissions needed), or None."""
    try:
        asn = subprocess.run(["lsappinfo", "front"], capture_output=True, text=True, timeout=5).stdout.strip()
        out = subprocess.run(["lsappinfo", "info", "-only", "name", asn], capture_output=True, text=True, timeout=5).stdout
        m = re.search(r'="(.*)"', out)
        return m.group(1) if m else None
    except (OSError, subprocess.SubprocessError):
        return None


@contextlib.contextmanager
def _keep_focus():
    """Give the screen back to whichever app was in front before we touched Arc."""
    prev = _front_app() if KEEP_FOCUS else None
    try:
        yield
    finally:
        if prev and prev != "Arc":
            time.sleep(0.2)  # Arc activates asynchronously after the script returns
            subprocess.run(["open", "-a", prev], capture_output=True, check=False)


def _window_id(run: Runner) -> str:
    """Id of the dedicated Arc window, creating it if it is missing or was closed."""
    try:
        saved = open(WINDOW_FILE).read().strip()
    except OSError:
        saved = ""
    if saved:
        try:
            run(f'tell application "Arc" to tell window id {_q(saved)} to return id of active tab')
            return saved
        except RuntimeError:
            pass
    wid = run('tell application "Arc"\nmake new window\nreturn id of front window\nend tell')
    with open(WINDOW_FILE, "w") as f:
        f.write(wid)
    return wid


def open_tab(url: str, run: Runner = run_applescript) -> str:
    """Open url in a new tab of the dedicated Arc window, in the background, and return the tab id."""
    # Arc can't return the id of a freshly made tab directly, so read it from the window's active tab;
    # a file lock keeps parallel callers from interleaving.
    with open(_LOCK_PATH, "w") as lock, _keep_focus():
        fcntl.flock(lock, fcntl.LOCK_EX)
        wid = _window_id(run)
        return run(
            f'tell application "Arc" to tell window id {_q(wid)}\n'
            f"make new tab with properties {{URL:{_q(url)}}}\n"
            "return id of active tab\n"
            "end tell"
        )


def close_window(run: Runner = run_applescript) -> None:
    """Close the dedicated automation window, if any."""
    try:
        wid = open(WINDOW_FILE).read().strip()
    except OSError:
        return
    with contextlib.suppress(RuntimeError, OSError):
        run(f'tell application "Arc" to close window id {_q(wid)}')
    with contextlib.suppress(OSError):
        os.remove(WINDOW_FILE)


def _in_any_window(tab_id: str, action: str) -> str:
    """AppleScript that runs `action` on the tab with this id, whichever Arc window currently holds it."""
    return (
        'tell application "Arc"\n'
        "repeat with w in windows\n"
        "try\n"
        f"tell w to tell tab id {_q(tab_id)} to {action}\n"
        "end try\n"
        "end repeat\n"
        "end tell"
    )


def tab_js(tab_id: str, js: str, run: Runner = run_applescript) -> str:
    """Execute JavaScript in the tab with the given id and return the result."""
    return run(_in_any_window(tab_id, f"return execute javascript {_q(js)}"))


def close_tab(tab_id: str, run: Runner = run_applescript) -> None:
    run(_in_any_window(tab_id, "close"))


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


def fetch_json_via_page(
    page_url: str,
    api_url: str,
    run: Runner = run_applescript,
    sleep: Callable[[float], None] = time.sleep,
    settle_seconds: float = 6.0,
    chunk: int = 40000,
    polls: int = 20,
    init: Optional[dict] = None,
) -> str:
    """Fetch api_url from inside page_url (so the user's cookies apply); return the body text.

    init is an optional fetch() options dict (e.g. method/headers/body for a POST)."""""
    tab_id = open_tab(page_url, run)
    try:
        sleep(settle_seconds)
        tab_js(
            tab_id,
            "window.__r=null;fetch(" + _json_str(api_url) + "," + _json_str({"credentials": "include", **(init or {})}) + ")"
            ".then(r=>r.text()).then(t=>{window.__r=t}).catch(e=>{window.__r='ERR '+e});'started'",
            run,
        )
        length = -1
        for _ in range(polls):
            sleep(1.5)
            length = int(_unquote(tab_js(tab_id, "String(window.__r===null?-1:window.__r.length)", run)))
            if length >= 0:
                break
        if length < 0:
            raise TimeoutError("page fetch did not complete")
        return "".join(_unquote(tab_js(tab_id, f"window.__r.slice({i},{i + chunk})", run)) for i in range(0, length, chunk))
    finally:
        close_tab(tab_id, run)


def _json_str(value: str) -> str:
    import json

    return json.dumps(value)


def _unquote(raw: str) -> str:
    """Arc returns JS strings JSON-quoted; undo that when present."""
    import json

    raw = raw.strip()
    if raw.startswith('"'):
        try:
            return json.loads(raw)
        except ValueError:
            pass
    return raw


if __name__ == "__main__":  # CLI: python -m clients.arc_browser <url> | --close-window
    import sys

    if sys.argv[1:] == ["--close-window"]:
        close_window()
    else:
        out = fetch_page_text(sys.argv[1])
        print(out if out is not None else "BLOCKED: login wall, CAPTCHA, or bot check")
