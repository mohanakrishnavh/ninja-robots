import pytest

from clients import arc_browser as ab


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(ab, "WINDOW_FILE", str(tmp_path / "win.id"))
    monkeypatch.setattr(ab, "KEEP_FOCUS", False)


def test_fetch_page_text_opens_reads_and_closes():
    calls = []

    def run(script):
        calls.append(script)
        if "make new window" in script:
            return "WIN-1"
        if "make new tab" in script:
            return "TAB-1"
        if "execute javascript" in script:
            return "Anthropic $887,500"
        return ""

    text = ab.fetch_page_text("https://example.com", run=run, sleep=lambda s: None)
    assert text == "Anthropic $887,500"
    assert any("tab id \"TAB-1\"" in c for c in calls) and "to close" in calls[-1]
    assert sum("make new window" in c for c in calls) == 1


def test_blocked_page_returns_none_and_still_closes():
    calls = []

    def run(script):
        calls.append(script)
        if "make new window" in script:
            return "W"
        if "make new tab" in script:
            return "T"
        return "Just a moment..." if "execute javascript" in script else ""

    assert ab.fetch_page_text("https://x", run=run, sleep=lambda s: None) is None
    assert "to close" in calls[-1]


def test_quote_escaping():
    assert ab._q('a"b') == '"a\\"b"'


def test_window_is_reused_and_recreated_when_closed():
    made = []

    def run(script):
        if "make new window" in script:
            made.append(1)
            return f"W{len(made)}"
        if "return id of active tab" in script and "make new tab" not in script:
            if 'window id "W1"' in script and len(made) >= 1 and closed:
                raise RuntimeError("gone")
            return "T"
        return "TAB"

    closed = False
    assert ab._window_id(run) == "W1"
    assert ab._window_id(run) == "W1" and len(made) == 1  # reused
    closed = True
    assert ab._window_id(run) == "W2" and len(made) == 2  # recreated


def test_front_app_parses_lsappinfo(monkeypatch):
    outputs = iter(["ASN:0x0-0x1234:\n", '"LSDisplayName"="Claude"\n'])

    class R:
        def __init__(self, out):
            self.stdout = out

    monkeypatch.setattr(ab.subprocess, "run", lambda *a, **k: R(next(outputs)))
    assert ab._front_app() == "Claude"
