"""Regenerate Companies/INDEX.md in the interview-prep repo from _ranking.md and per-company folders.

Ranked companies come from the table in Companies/_ranking.md. Companies with a folder but no ranking
row (e.g. FAANG) are listed separately using their summary.json.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

ROW = re.compile(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\$[\d,]+)\s*\|")


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def updated(readme: Path) -> str:
    m = re.search(r"_Last updated:\s*([0-9-]+)", readme.read_text()) if readme.exists() else None
    return m.group(1) if m else ""


def ranked_rows(ranking: Path) -> List[tuple]:
    return [m.groups() for m in map(ROW.match, ranking.read_text().splitlines()) if m] if ranking.exists() else []


def money(n: Optional[float]) -> str:
    return f"${int(n):,}" if n else "n/a"


def render(companies_dir: Path) -> str:
    rows = ranked_rows(companies_dir / "_ranking.md")
    ranked_slugs = {slugify(name) for _, name, _, _ in rows}
    out = ["# Companies", "",
           "Senior Software Engineer and Forward Deployed Engineer research. Ranked rows come from the levels.fyi "
           "Senior Engineer (US) leaderboard ([_ranking.md](./_ranking.md)).", "",
           "| Rank | Company | Level shown | Total comp | Updated | Notes |", "|---|---|---|---|---|---|"]
    for rank, name, level, total in rows:
        slug = slugify(name)
        readme = companies_dir / slug / "README.md"
        if readme.exists():
            out.append(f"| {rank} | [{name}](./{slug}/README.md) | {level} | {total} | {updated(readme)} | [changelog](./{slug}/changelog.md) |")
        else:
            out.append(f"| {rank} | {name} | {level} | {total} |  | not researched |")
    extra = sorted(d for d in companies_dir.iterdir() if d.is_dir() and d.name not in ranked_slugs and (d / "README.md").exists())
    if extra:
        out += ["", "## Also researched (not in the captured leaderboard rows)", "",
                "| Company | Level | Total comp | Updated | Notes |", "|---|---|---|---|---|"]
        for d in extra:
            s = json.loads((d / "summary.json").read_text()) if (d / "summary.json").exists() else {}
            out.append(f"| [{s.get('name', d.name)}](./{d.name}/README.md) | {s.get('level', '')} | {money(s.get('total'))} | "
                       f"{updated(d / 'README.md')} | [changelog](./{d.name}/changelog.md) |")
    return "\n".join(out) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="company_index")
    ap.add_argument("--companies-dir", type=Path, default=Path("~/Repos/interview-prep/Companies").expanduser())
    a = ap.parse_args(argv)
    (a.companies_dir / "INDEX.md").write_text(render(a.companies_dir))
    print(f"wrote {a.companies_dir / 'INDEX.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
