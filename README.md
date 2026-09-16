# ninja-robots

Reusable Python building blocks and Claude skills.

## Layout

- `clients/` — reusable, importable Python modules (platform API/scraping clients, shared helpers). Not tied to any one skill.
- `data/` — static reference data in JSON (filter codes, config), loaded by clients instead of being hardcoded.
- `skills/` — Claude skill manifests (`SKILL.md`) that describe when/how to use the clients in `clients/`.
- `tests/` — dedicated eval/test suites for each skill's client, run against fixture HTML (no live network) so they're deterministic.

## Skills

- `skills/linkedin-job-search` — search public LinkedIn job postings via `clients/linkedin_client.py`.
  - `skills/linkedin-job-search/evals/evals.json` — trigger-style eval prompts for this skill.
- `skills/indeed-job-search` — search public Indeed job postings via `clients/indeed_client.py`.
  - `skills/indeed-job-search/evals/evals.json` — trigger-style eval prompts for this skill.

## Setup

```bash
pip install -r requirements.txt
```

## Testing

Each skill has a dedicated eval/test suite:

- `tests/test_linkedin_client.py`, `tests/test_indeed_client.py` — deterministic tests of each client's request-building and HTML-parsing logic, run against fixture pages in `tests/fixtures/` (no live network calls, since LinkedIn/Indeed markup and bot-protection make live scraping unreliable to depend on in CI).
- `skills/<skill-name>/evals/evals.json` — realistic trigger prompts (and negative cases) describing when/how each skill should be invoked, per the skill-creator eval schema.

Run the deterministic suite with:

```bash
pytest tests/
```
