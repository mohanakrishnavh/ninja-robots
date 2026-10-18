from pathlib import Path

from clients import dsa_sheet as ds

TPL = "https://x/?open={id}"
SYL = [{"id": 1, "slug": "arrays", "type": "category", "label": "Arrays", "children": [
    {"id": 2, "slug": "easy", "type": "category", "label": "Easy", "children": [
        {"id": 10, "slug": "two-sum", "type": "problem", "label": "Two Sum", "redirectTo": {"layoutType": "practice"}},
        {"id": 11, "slug": "intro", "type": "problem", "label": "Intro", "redirectTo": {"layoutType": "theory"}}]}]}]


def test_flatten_paths_and_kinds():
    probs = ds.flatten(SYL, TPL)
    assert [p.rel_dir for p in probs] == ["01-arrays/easy/01-two-sum", "01-arrays/easy/02-intro"]
    assert [p.kind for p in probs] == ["practice", "theory"]
    assert probs[0].url == "https://x/?open=10"


def test_scan_and_missing_notes(tmp_path: Path):
    probs = ds.flatten(SYL, TPL)
    ds.start_problem(tmp_path, probs[0])
    assert not ds.scan(tmp_path, probs)[10].solved  # README stub only
    (tmp_path / probs[0].rel_dir / "Solution.java").write_text("class S {}")
    st = ds.scan(tmp_path, probs)
    assert st[10].solved and [p.id for p in ds.missing_notes(probs, st)] == [10]
    (tmp_path / probs[0].rel_dir / "NOTES.md").write_text("n")
    assert ds.missing_notes(probs, ds.scan(tmp_path, probs)) == []


def test_sync_writes_index(tmp_path: Path):
    ds.sync(tmp_path, SYL, TPL)
    assert (tmp_path / "sheet.json").is_file() and "Two Sum" in (tmp_path / "README.md").read_text()
