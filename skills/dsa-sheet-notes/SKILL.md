---
name: dsa-sheet-notes
description: On-demand tracker for Striver's A2Z DSA sheet in the interview-prep repo's code/ folder. Scans which problems the user has solved (solution files present) but lacks NOTES.md, then spawns dsa-notes-writer agents to write visual notes (Mermaid diagrams, multiple approaches), refreshes progress, and commits. Also starts a problem folder or re-syncs the sheet. Use when the user says things like "write DSA notes", "update my DSA progress", "start problem X", or "sync the A2Z sheet".
---

# DSA sheet notes

Code lives in `~/Repos/interview-prep/code/` (clone `https://github.com/mohanakrishnavh/interview-prep.git` if missing; `git pull --ff-only` first). Helper CLI, run from the ninja-robots repo root: `python3 -m clients.dsa_sheet <command>`. Config: `data/dsa_sheet_sources.json`.

Layout: `code/sheet.json` (the sheet), `code/README.md` (generated index with ✅/✍️/⬜ per problem), and one folder per problem `code/<NN-section>/<topic>/<NN-problem>/` holding the user's solution files, an optional `README.md` stub, and `NOTES.md`. **Solved** = any file besides README/NOTES in the folder, or marked done in the app (`code/progress.db` (SQLite, checked in); marked-only problems get no notes since there is no code). **Noted** = `NOTES.md` exists.

## Commands

- **Start a problem** ("start two-sum"): `python3 -m clients.dsa_sheet start <slug-or-id>` creates the folder + README stub; tell the user the path.
- **Scaffold folders**: `python3 -m clients.dsa_sheet scaffold` creates a folder with a README stub (links to video, article, LeetCode) for every practice problem. It writes only README stubs, never solution files, because any other file would count as solved. Run it after `sync` to pick up new problems.
- **Write notes** (the main on-demand flow):
  1. `python3 -m clients.dsa_sheet missing` lists solved problems with no `NOTES.md` (id, folder, label, files). If none, say so and stop.
  2. Spawn one `dsa-notes-writer` agent per problem (all calls of a batch in one message; batches of 5), passing the folder, label, and link. Agents write only in their folder.
  3. `python3 -m clients.dsa_sheet refresh` to update the README index counts.
  4. In interview-prep: `git add Code && git commit -m "dsa: notes for <n> problems"` and push. Stage only `code/`.
  5. Report: problems noted, any "Review" findings agents raised about the user's code.
- **Re-notes**: if the user asks to regenerate a problem's notes (or the solution changed), delete that `NOTES.md` first, then run the flow.
- **Sync the sheet** (the sheet changed upstream): `python3 -m clients.dsa_sheet sync` fetches it (and each problem's YouTube, article and LeetCode links) through a dedicated background window in the user's signed-in Arc (`clients/arc_browser.py`; no credentials handled; focus is handed back to the app in front). Existing solution folders are untouched; rename detection isn't automatic, so check `git status` after.

## Rules

- Never edit or delete the user's solution files.
- Progress is derived from files; don't hand-edit checkmarks in `README.md` (they're regenerated).
- Theory items in the sheet are tracked in the index but get no notes.
