# ninja-robots

## Coding conventions

- Write Python code as reusable, importable functions/modules rather than one-off scripts, since it will be used to build Claude skills. Favor clear function signatures, avoid hardcoded/inline assumptions, and keep logic decoupled from any specific skill's I/O so it can be imported across multiple skills.
- Store reusable static data in JSON files rather than hardcoding it inline in Python.
- Keep the repo organized into folders by purpose as it grows (e.g. separate directories for skills, reusable Python modules, and JSON data), rather than accumulating files at the repo root.
- Write dedicated evals for each skill: deterministic tests for the skill's underlying client(s) under `tests/` (using fixture data, not live network calls, so they run reliably in CI), plus a `skills/<skill-name>/evals/evals.json` file with realistic trigger prompts and assertions per the skill-creator schema.
