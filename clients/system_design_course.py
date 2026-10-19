"""Mirror an Educative course (default: Grokking the System Design Interview) into interview-prep/system-design/.

Reads the course's table of contents from Educative's collection API through the user's signed-in Arc
(clients.arc_browser), writes `system-design/course.json`, and scaffolds one folder per lesson with a
README stub (link + room for NOTES.md). Progress (lessons marked done) is kept by the app in
`system-design/progress.db`; this module only reads it.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set

COURSE_SLUG = "grokking-the-system-design-interview"
COURSE_URL = f"https://www.educative.io/courses/{COURSE_SLUG}"
API_URL = f"https://www.educative.io/api/collection/{COURSE_SLUG}?work_type=collection"
DEFAULT_ROOT = Path("~/Repos/interview-prep/system-design").expanduser()

# A part starts at the module with this title and runs until the next listed one. New modules join the current part.
PART_STARTS = {
    "Introduction": "Foundations",
    "Building Blocks": "Building blocks",
    "Design YouTube": "Design problems",
    "System Design Shift in AI": "AI systems",
    "Lessons from System Failures": "Wrap-up and extras",
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def _clean(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip()


def parse_collection(data: dict) -> dict:
    """Turn Educative's collection JSON into {title,url,parts:[{title,dir,modules:[{title,dir,lessons:[...]}]}]}."""
    details = data["instance"]["details"] if "instance" in data else data["details"]
    modules: List[dict] = []
    part_title = "Course"
    for cat in details["toc"]["categories"]:
        title = _clean(cat["title"])
        if cat.get("type") == "LINKED_MOCK_INTERVIEW":
            if modules:  # AI mock interviews run inside the Educative app; link to the course
                modules[-1]["lessons"].append({"id": f"mock-{cat['id']}", "title": f"Mock interview: {title}", "kind": "mock",
                                               "url": COURSE_URL, "preview": False})
            continue
        part_title = PART_STARTS.get(title, part_title)
        lessons = [{"id": str(p["page_id"]), "title": _clean(p["title"]), "kind": "lesson", "preview": bool(p.get("is_preview")),
                    "url": f"{COURSE_URL}/{p['slug']}"} for p in cat.get("pages", [])]
        modules.append({"part": part_title, "title": title, "lessons": lessons})
    parts: List[dict] = []
    for m in modules:
        if not parts or parts[-1]["title"] != m["part"]:
            parts.append({"title": m["part"], "modules": []})
        parts[-1]["modules"].append({"title": m["title"], "lessons": m["lessons"]})
    for pi, part in enumerate(parts, 1):
        part["dir"] = f"{pi:02d}-{slugify(part['title'])}"
        for mi, mod in enumerate(part["modules"], 1):
            mod["id"] = slugify(mod["title"])
            mod["dir"] = f"{part['dir']}/{mi:02d}-{mod['id']}"
            for li, les in enumerate(mod["lessons"], 1):
                les["dir"] = f"{mod['dir']}/{li:02d}-{slugify(les['title'])[:60]}"
    return {"title": _clean(details.get("title", "System design course")), "slug": COURSE_SLUG, "url": COURSE_URL, "parts": parts}


def lessons_of(course: dict):
    for part in course["parts"]:
        for mod in part["modules"]:
            for les in mod["lessons"]:
                yield part, mod, les


def stub_text(course: dict, mod: dict, les: dict) -> str:
    where = "AI mock interview (open from the course sidebar)" if les["kind"] == "mock" else "Lesson"
    return (f"# {les['title']}\n\n- Course: {course['title']} › {mod['title']}\n- {where}: {les['url']}\n\n"
            "Put your notes in `NOTES.md` here, plus any diagrams or sketches you draw while studying.\n")


def scaffold(root: Path, course: dict) -> int:
    """Create a folder with a README stub per lesson; returns how many were new. Never touches existing files."""
    created = 0
    for _, mod, les in lessons_of(course):
        d = root / les["dir"]
        d.mkdir(parents=True, exist_ok=True)
        readme = d / "README.md"
        if not readme.exists():
            readme.write_text(stub_text(course, mod, les))
            created += 1
    return created


def load_marks(root: Path) -> Set[str]:
    """Item ids marked done in the app (rows of system-design/progress.db); empty if missing or unreadable."""
    db = root / "progress.db"
    if not db.is_file():
        return set()
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            return {row[0] for row in conn.execute("SELECT item_id FROM sd_progress")}
        finally:
            conn.close()
    except sqlite3.Error:
        return set()


def render_readme(course: dict, marks: Set[str], noted: Optional[Set[str]] = None) -> str:
    noted = noted or set()
    total = sum(1 for _ in lessons_of(course))
    done = sum(1 for _, _, l in lessons_of(course) if l["id"] in marks)
    out = [f"# System Design — {course['title']}", "",
           f"**Done:** {done} / {total} · course: {course['url']}", "", "☑️ done · ⬜ not started · 📝 has notes", ""]
    for part in course["parts"]:
        out += ["", f"## {part['title']}"]
        for mod in part["modules"]:
            out += ["", f"### {mod['title']}", ""]
            for les in mod["lessons"]:
                mark = "☑️" if les["id"] in marks else "⬜"
                out.append(f"- {mark} [{les['title']}]({les['url']}){' 📝' if les['id'] in noted else ''}")
    return "\n".join(out) + "\n"


def noted_ids(root: Path, course: dict) -> Set[str]:
    return {l["id"] for _, _, l in lessons_of(course) if (root / l["dir"] / "NOTES.md").is_file()}


def load_course(root: Path) -> dict:
    return json.loads((root / "course.json").read_text())


def sync(root: Path, data: dict) -> dict:
    course = parse_collection(data)
    root.mkdir(parents=True, exist_ok=True)
    (root / "course.json").write_text(json.dumps(course, indent=1) + "\n")
    scaffold(root, course)
    (root / "README.md").write_text(render_readme(course, load_marks(root), noted_ids(root, course)))
    return course


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="system_design_course")
    ap.add_argument("command", choices=["sync", "scaffold", "refresh"])
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--from-file", type=Path, help="saved collection JSON instead of fetching via Arc")
    a = ap.parse_args(argv)
    if a.command == "sync":
        if a.from_file:
            data = json.loads(a.from_file.read_text())
        else:
            from clients.arc_browser import fetch_json_via_page

            data = json.loads(fetch_json_via_page(COURSE_URL, API_URL))
        course = sync(a.root, data)
        print(f"synced {sum(1 for _ in lessons_of(course))} items in {sum(len(p['modules']) for p in course['parts'])} modules into {a.root}")
        return 0
    course = load_course(a.root)
    if a.command == "scaffold":
        print(f"created {scaffold(a.root, course)} lesson folders")
    else:
        (a.root / "README.md").write_text(render_readme(course, load_marks(a.root), noted_ids(a.root, course)))
        print("README refreshed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
