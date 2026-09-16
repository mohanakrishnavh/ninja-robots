# ninja-robots

Reusable Python building blocks and Claude skills.

## Layout

- `clients/` — reusable, importable Python modules (platform API/scraping clients, shared helpers). Not tied to any one skill.
- `data/` — static reference data in JSON (filter codes, config), loaded by clients instead of being hardcoded.
- `skills/` — Claude skill manifests (`SKILL.md`) that describe when/how to use the clients in `clients/`.

## Skills

- `skills/linkedin-job-search` — search public LinkedIn job postings via `clients/linkedin_client.py`.
- `skills/indeed-job-search` — search public Indeed job postings via `clients/indeed_client.py`.

## Setup

```bash
pip install -r requirements.txt
```
