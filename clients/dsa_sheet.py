"""Mirror Striver's A2Z DSA sheet into a local Code/ folder and track progress.

A problem counts as *solved* when its folder holds at least one file other than the
README/NOTES stubs, and as *noted* when it has a NOTES.md. Everything is derived from the
filesystem, so progress needs no separate bookkeeping.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "dsa_sheet_sources.json"


def load_config(path: Path = DATA_FILE) -> dict:
    return json.loads(path.read_text())


@dataclass
class Problem:
    id: int
    slug: str
    label: str
    kind: str  # "practice" or "theory"
    path: List[tuple]  # [(category_slug, category_label), ...]
    order: int
    url: str
    rel_dir: str = ""


@dataclass
class Status:
    solutions: List[str] = field(default_factory=list)
    has_notes: bool = False

    @property
    def solved(self) -> bool:
        return bool(self.solutions)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def flatten(syllabus: list, url_template: str) -> List[Problem]:
    """Depth-first flatten of the syllabus tree into ordered Problems with folder paths."""
    out: List[Problem] = []

    def walk(nodes: list, path: List[tuple], counters: Dict[tuple, int]) -> None:
        for node in nodes:
            if node["type"] == "category":
                walk(node.get("children", []), path + [(node["slug"], node["label"])], counters)
            elif node["type"] == "problem":
                key = tuple(s for s, _ in path)
                counters[key] = counters.get(key, 0) + 1
                n = counters[key]
                kind = (node.get("redirectTo") or {}).get("layoutType", "practice")
                rel = "/".join(
                    [f"{i + 1:02d}-{slugify(s)}" for i, (s, _) in enumerate(path[:1])]
                    + [slugify(s) for s, _ in path[1:]]
                    + [f"{n:02d}-{slugify(node['slug'])}"]
                )
                out.append(Problem(node["id"], node["slug"], node["label"], "theory" if kind == "theory" else "practice",
                                   list(path), n, url_template.format(id=node["id"]), rel))

    walk(syllabus, [], {})
    # prefix top-level sections with their position so folders sort like the sheet
    sections = {}
    for p in out:
        sections.setdefault(p.path[0][0] if p.path else "", len(sections) + 1)
    for p in out:
        top = p.path[0][0] if p.path else ""
        p.rel_dir = re.sub(r"^\d+-", f"{sections[top]:02d}-", p.rel_dir, count=1)
    return out


def scan(code_root: Path, problems: Iterable[Problem], ignored_files=("README.md", "NOTES.md", ".DS_Store"),
         ignored_dirs=("assets",)) -> Dict[int, Status]:
    status: Dict[int, Status] = {}
    for p in problems:
        d = code_root / p.rel_dir
        st = Status()
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.name not in ignored_files:
                    st.solutions.append(f.name)
            st.has_notes = (d / "NOTES.md").is_file()
        status[p.id] = st
    return status


def missing_notes(problems: Iterable[Problem], status: Dict[int, Status]) -> List[Problem]:
    """Practice problems that have solution code but no NOTES.md."""
    return [p for p in problems if p.kind == "practice" and status[p.id].solved and not status[p.id].has_notes]


def start_problem(code_root: Path, p: Problem) -> Path:
    """Create the problem folder with a README stub (idempotent). Returns the folder."""
    d = code_root / p.rel_dir
    d.mkdir(parents=True, exist_ok=True)
    readme = d / "README.md"
    if not readme.exists():
        trail = " › ".join(label for _, label in p.path)
        readme.write_text(f"# {p.label}\n\n- Sheet: {trail}\n- Link: {p.url}\n\nPut your solution file(s) in this folder "
                          f"(any language). Ask Claude to \"write DSA notes\" to generate `NOTES.md`.\n")
    return d


def render_readme(problems: List[Problem], status: Dict[int, Status]) -> str:
    practice = [p for p in problems if p.kind == "practice"]
    solved = sum(status[p.id].solved for p in practice)
    noted = sum(status[p.id].has_notes for p in practice)
    lines = ["# Code — Striver's A2Z DSA Sheet", "",
             f"**Solved:** {solved} / {len(practice)} · **With notes:** {noted} · generated from `sheet.json`", "",
             "Legend: ✅ solved + notes · ✍️ solved, notes missing · ⬜ not started · 📖 theory", ""]
    last: Optional[tuple] = None
    for p in problems:
        trail = tuple(l for _, l in p.path)
        if trail != last:
            if not last or trail[:1] != last[:1]:
                lines += ["", f"## {trail[0] if trail else 'General'}"]
            if len(trail) > 1:
                lines += ["", f"### {' › '.join(trail[1:])}"]
            lines.append("")
            last = trail
        st = status[p.id]
        mark = "📖" if p.kind == "theory" else "✅" if st.has_notes and st.solved else "✍️" if st.solved else "⬜"
        link = f"[{p.label}]({p.url})"
        local = f" · [code](./{p.rel_dir}/)" if (st.solved or st.has_notes) else ""
        lines.append(f"- {mark} {link}{local}")
    return "\n".join(lines) + "\n"


def sync(code_root: Path, syllabus: list, url_template: str) -> List[Problem]:
    """Write sheet.json + README.md under code_root from a fetched syllabus; keep user files."""
    problems = flatten(syllabus, url_template)
    code_root.mkdir(parents=True, exist_ok=True)
    (code_root / "sheet.json").write_text(json.dumps(
        [{"id": p.id, "slug": p.slug, "label": p.label, "kind": p.kind, "dir": p.rel_dir, "url": p.url,
          "sections": [l for _, l in p.path]} for p in problems], indent=1) + "\n")
    (code_root / "README.md").write_text(render_readme(problems, scan(code_root, problems)))
    return problems


def load_problems(code_root: Path) -> List[Problem]:
    rows = json.loads((code_root / "sheet.json").read_text())
    return [Problem(r["id"], r["slug"], r["label"], r["kind"], [(slugify(s), s) for s in r["sections"]], 0, r["url"], r["dir"])
            for r in rows]


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="dsa_sheet")
    ap.add_argument("command", choices=["sync", "refresh", "missing", "start"])
    ap.add_argument("name", nargs="?", help="problem slug or id for 'start'")
    ap.add_argument("--code-root", type=Path)
    ap.add_argument("--from-file", type=Path, help="syllabus JSON (the 'data.syllabus' list) instead of fetching via Arc")
    a = ap.parse_args(argv)
    cfg = load_config()
    root = a.code_root or Path(cfg["interview_prep_repo"]).expanduser() / cfg["code_dir"]
    if a.command == "sync":
        if a.from_file:
            syllabus = json.loads(a.from_file.read_text())
        else:
            from clients.arc_browser import fetch_json_via_page

            syllabus = json.loads(fetch_json_via_page(cfg["sheet_page_url"], cfg["sheet_api_url"]))["data"]["syllabus"]
        probs = sync(root, syllabus, cfg["problem_url_template"])
        print(f"synced {len(probs)} items into {root}")
        return 0
    probs = load_problems(root)
    st = scan(root, probs, cfg["ignored_files"], cfg["ignored_dirs"])
    if a.command == "refresh":
        (root / "README.md").write_text(render_readme(probs, st))
        print("README refreshed")
    elif a.command == "missing":
        for p in missing_notes(probs, st):
            print(f"{p.id}\t{p.rel_dir}\t{p.label}\t{','.join(st[p.id].solutions)}")
    elif a.command == "start":
        match = [p for p in probs if a.name in (p.slug, str(p.id))]
        if not match:
            print("no such problem")
            return 1
        print(start_problem(root, match[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
