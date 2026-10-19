import sqlite3
from pathlib import Path

from clients import system_design_course as sd


def page(i, title, slug, preview=False):
    return {"page_id": i, "title": title, "slug": slug, "is_preview": preview, "type": "collection_lesson"}


DATA = {"instance": {"details": {"title": "Grokking Test", "toc": {"categories": [
    {"id": "a", "title": "Introduction", "type": "COLLECTION_CATEGORY", "pages": [page(1, "Intro  to Design", "intro", True)]},
    {"id": "b", "title": "Building Blocks", "type": "COLLECTION_CATEGORY", "pages": [page(2, "Load Balancers", "load-balancers"), page(3, "DNS", "dns")]},
    {"id": "cache-mock", "title": "Distributed Cache System Design", "type": "LINKED_MOCK_INTERVIEW", "pages": []},
    {"id": "c", "title": "Design YouTube", "type": "COLLECTION_CATEGORY", "pages": [page(4, "YouTube", "youtube")]},
]}}}}


def test_parse_groups_into_parts_modules_lessons_and_attaches_mocks():
    c = sd.parse_collection(DATA)
    assert [p["title"] for p in c["parts"]] == ["Foundations", "Building blocks", "Design problems"]
    bb = c["parts"][1]["modules"][0]
    assert [l["title"] for l in bb["lessons"]] == ["Load Balancers", "DNS", "Mock interview: Distributed Cache System Design"]
    assert bb["lessons"][0]["url"] == f"{sd.COURSE_URL}/load-balancers" and bb["lessons"][2]["kind"] == "mock"
    assert c["parts"][0]["modules"][0]["lessons"][0]["title"] == "Intro to Design"  # whitespace collapsed
    assert c["parts"][1]["modules"][0]["lessons"][0]["dir"] == "02-building-blocks/01-building-blocks/01-load-balancers"


def test_sync_scaffold_is_idempotent_and_never_overwrites(tmp_path: Path):
    c = sd.sync(tmp_path, DATA)
    folder = tmp_path / c["parts"][0]["modules"][0]["lessons"][0]["dir"]
    (folder / "README.md").write_text("mine")
    assert sd.scaffold(tmp_path, c) == 0 and (folder / "README.md").read_text() == "mine"
    assert (tmp_path / "course.json").is_file() and "Load Balancers" in (tmp_path / "README.md").read_text()


def test_marks_and_readme_progress(tmp_path: Path):
    c = sd.sync(tmp_path, DATA)
    assert sd.load_marks(tmp_path) == set()  # no db yet and none is created
    assert not (tmp_path / "progress.db").exists()
    conn = sqlite3.connect(tmp_path / "progress.db")
    conn.execute("CREATE TABLE sd_progress (item_id TEXT PRIMARY KEY, done_at TEXT NOT NULL)")
    conn.execute("INSERT INTO sd_progress VALUES ('2', '2026-01-01')")
    conn.commit()
    conn.close()
    md = sd.render_readme(c, sd.load_marks(tmp_path))
    assert "**Done:** 1 / 5" in md and "☑️ [Load Balancers]" in md and "⬜ [DNS]" in md
