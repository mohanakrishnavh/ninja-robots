---
name: indeed-job-search
description: Search Indeed job postings by keywords, location, and filters (remote, job type, date posted, radius), publicly or via the authenticated Publisher API. Use when the user wants to find or search jobs on Indeed.
---

# Indeed Job Search

Use `clients/indeed_client.py`'s `IndeedJobClient` to search Indeed job listings.

## Authentication

- **No credentials (default):** scrapes Indeed's public search results page — no login or API key needed.
- **`INDEED_PUBLISHER_ID` set:** calls Indeed's key-based Publisher API for structured JSON results instead of scraping HTML. Set this environment variable to the publisher ID — **never hardcode it in code or commit it to source control.** Note Indeed has largely closed this program to new applicants, so a working publisher ID may not be obtainable for a new account.

`client.is_authenticated` reports which mode is active.

## Usage

```python
from clients.indeed_client import IndeedJobClient

client = IndeedJobClient()  # reads INDEED_PUBLISHER_ID from the environment if set
jobs = client.search(
    keywords="data analyst",
    location="Austin, TX",
    remote_only=False,
    job_type="full_time",     # see data/job_search_config.json -> indeed.job_types
    date_posted="last_7",     # any_time | last_1 | last_3 | last_7 | last_14
    radius_miles=25,
    max_results=25,
)

for job in jobs:
    print(job.title, job.company, job.location, job.url)
```

## Notes

- Indeed changes its public-page markup fairly often and may show CAPTCHAs to automated traffic in the unauthenticated mode. Keep `max_results` modest and don't remove the client's built-in delay between paginated requests.
- To search a different country's Indeed site, pass `country_domain="uk.indeed.com"` (etc.) when constructing `IndeedJobClient` (unauthenticated mode only).
- Filter values (job types, date-posted windows) live in `data/job_search_config.json` under `indeed`. Update that file if Indeed changes its filter parameters — don't hardcode new values in the client.
- Returns a list of `JobPosting` objects (`clients/common.py`) with `title`, `company`, `location`, `url`, `job_id` (plus `posted_at`/`description` in Publisher API mode).
- Site markup/API responses can change over time; if parsing starts returning zero results, check `_parse_public_page` (public mode) or `_parse_publisher_results` (Publisher API mode) in `clients/indeed_client.py` against the current response.
- Neither mode has been verified against a live Indeed endpoint in this environment (outbound network to indeed.com is blocked here) — request-building and response-parsing logic is covered by `tests/test_indeed_client.py` / `tests/test_indeed_client_authenticated.py` against fixtures, but confirm it works before relying on it.
