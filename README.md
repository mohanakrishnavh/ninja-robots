# ninja-robots

Reusable Python building blocks and Claude skills.

## Layout

- `clients/` — reusable, importable Python modules (platform API/scraping clients, shared helpers). Not tied to any one skill.
- `data/` — static reference data in JSON (filter codes, config), loaded by clients instead of being hardcoded.
- `skills/` — Claude skill manifests (`SKILL.md`) that describe when/how to use the clients in `clients/`.
- `tests/` — dedicated eval/test suites for each skill's client, run against fixture HTML (no live network) so they're deterministic.

## Skills

- `skills/linkedin-job-search` — search LinkedIn job postings via `clients/linkedin_client.py`, as a guest or (with `LINKEDIN_LI_AT_COOKIE`) as an authenticated user.
  - `skills/linkedin-job-search/evals/evals.json` — trigger-style eval prompts for this skill.
- `skills/indeed-job-search` — search Indeed job postings via `clients/indeed_client.py`, publicly or (with `INDEED_PUBLISHER_ID`) via the Publisher API.
  - `skills/indeed-job-search/evals/evals.json` — trigger-style eval prompts for this skill.

## Setup

```bash
pip install -r requirements.txt
```

### Credentials (optional)

Both clients work without any credentials (public/guest access). To enable authenticated access, copy `.env.example` to `.env`, fill in the values, and export them (or source `.env`) before running — **never hardcode credentials in code**. See each `.env.example` entry, or the "Authentication" section of the relevant `SKILL.md`, for what each variable does and the tradeoffs of using it.

## Testing

Each skill has a dedicated eval/test suite, covering both its public and authenticated modes:

- `tests/test_linkedin_client.py`, `tests/test_indeed_client.py` — deterministic tests of each client's public-mode request-building and parsing logic.
- `tests/test_linkedin_client_authenticated.py`, `tests/test_indeed_client_authenticated.py` — deterministic tests of each client's authenticated-mode credential handling and response parsing.
- All of the above run against fixtures in `tests/fixtures/` — no live network calls, since LinkedIn/Indeed markup, API responses, and bot-protection make live requests unreliable to depend on in CI.
- `skills/<skill-name>/evals/evals.json` — realistic trigger prompts (and negative cases) describing when/how each skill should be invoked, per the skill-creator eval schema.

Run the deterministic suite with:

```bash
pytest tests/
```
