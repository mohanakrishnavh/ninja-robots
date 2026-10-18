import json
from pathlib import Path

from clients import company_index as ci


def test_render_ranked_and_unranked(tmp_path: Path):
    (tmp_path / "_ranking.md").write_text("| 1 | Acme | L5 | $500,000 | 1K / 2K / N/A |\n| 2 | Beta | L4 | $400,000 | x |\n")
    (tmp_path / "acme").mkdir()
    (tmp_path / "acme" / "README.md").write_text("_Last updated: 2026-10-18 · rank #1_")
    (tmp_path / "meta").mkdir()
    (tmp_path / "meta" / "README.md").write_text("_Last updated: 2026-10-17_")
    (tmp_path / "meta" / "summary.json").write_text(json.dumps({"name": "Meta", "level": "E5", "total": 460000}))
    md = ci.render(tmp_path)
    assert "[Acme](./acme/README.md)" in md and "Beta | L4 | $400,000 |  | not researched" in md
    assert "| [Meta](./meta/README.md) | E5 | $460,000 | 2026-10-17" in md
