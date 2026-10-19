"""Extract per-problem resource links (YouTube video, article, LeetCode) from takeUforward's sheet page.

The sheet page embeds every row as a compact JSON array in its server-rendered payload:
  [kind, id, "slug", "item", "practice", "Label", "17 min", {redirectTo}, "<youtube>", "<article path>", "<leetcode>", ...]
Lessons ("learning" rows) omit the duration and the LeetCode link. We parse each array as JSON and read
the fields that follow the redirectTo object.
"""
from __future__ import annotations

import json
import re
from typing import Dict, Optional

SITE = "https://takeuforward.org"
_START = re.compile(r'\[\d+,(\d+),"([^"]+)","item","(\w+)",')


def _array_at(text: str, start: int) -> str:
    """Return the balanced [...] array beginning at text[start], honouring JSON strings."""
    depth, i, in_str = 0, start, False
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    raise ValueError("unbalanced array")


def parse_links(page_html: str) -> Dict[int, dict]:
    """Map problem id → {slug, layout, youtube, article, leetcode, duration}; missing links are None."""
    text = page_html.replace('\\"', '"')
    out: Dict[int, dict] = {}
    for m in _START.finditer(text):
        try:
            arr = json.loads(_array_at(text, m.start()))
        except ValueError:
            continue
        d = next((i for i, v in enumerate(arr) if isinstance(v, dict) and "itemSlug" in v), None)
        if d is None:
            continue
        tail = arr[d + 1 : d + 4]
        youtube = next((v for v in tail if isinstance(v, str) and re.match(r"https?://(www\.)?(youtu\.be|youtube\.com)", v)), None)
        article = next((v for v in tail if isinstance(v, str) and v.startswith("/blogs/")), None)
        leetcode = next((v for v in tail if isinstance(v, str) and v.startswith("http") and v != youtube), None)
        duration = arr[d - 1] if d >= 6 and isinstance(arr[d - 1], str) else None
        out[int(m.group(1))] = {"slug": m.group(2), "layout": m.group(3), "youtube": youtube,
                                "article": SITE + article if article else None, "leetcode": leetcode, "duration": duration}
    return out


def fetch_links(page_url: str, fetch=None) -> Dict[int, dict]:
    """Fetch the sheet page through the user's signed-in Arc and parse its links."""
    if fetch is None:
        from clients.arc_browser import fetch_json_via_page as fetch
    return parse_links(fetch(page_url, page_url))
