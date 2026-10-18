from clients import arc_browser as ab


def test_fetch_page_text_opens_reads_and_closes():
    calls = []

    def run(script):
        calls.append(script)
        if "make new tab" in script:
            return "TAB-1"
        if "execute javascript" in script:
            return "Anthropic $887,500"
        return ""

    text = ab.fetch_page_text("https://example.com", run=run, sleep=lambda s: None)
    assert text == "Anthropic $887,500"
    assert "tab id \"TAB-1\"" in calls[1] and calls[-1].endswith("to close")


def test_blocked_page_returns_none_and_still_closes():
    calls = []

    def run(script):
        calls.append(script)
        if "make new tab" in script:
            return "T"
        return "Just a moment..." if "execute javascript" in script else ""

    assert ab.fetch_page_text("https://x", run=run, sleep=lambda s: None) is None
    assert calls[-1].endswith("to close")


def test_quote_escaping():
    assert ab._q('a"b') == '"a\\"b"'
