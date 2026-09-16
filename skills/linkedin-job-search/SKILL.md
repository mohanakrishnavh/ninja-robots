---
name: linkedin-job-search
description: Search LinkedIn job postings by keywords, location, and filters (remote, experience level, job type, date posted), as a guest or as an authenticated user. Use when the user wants to find or search jobs on LinkedIn.
---

# LinkedIn Job Search

Use `clients/linkedin_client.py`'s `LinkedInJobClient` to search LinkedIn job listings.

## Authentication

- **No credentials (default):** searches as an anonymous guest via LinkedIn's public "jobs-guest" endpoint.
- **`LINKEDIN_LI_AT_COOKIE` set:** searches as that logged-in user via LinkedIn's internal Voyager API, for richer/less rate-limited results. Set this environment variable to the account's `li_at` session cookie value (from browser dev tools) — **never hardcode it in code or commit it to source control.** This is automated use of a personal account against LinkedIn's Terms of Service and can get the account rate-limited or restricted; only do this with an account and request volume the user is comfortable with.

`client.is_authenticated` reports which mode is active.

## Usage

```python
from clients.linkedin_client import LinkedInJobClient

client = LinkedInJobClient()  # reads LINKEDIN_LI_AT_COOKIE from the environment if set
jobs = client.search(
    keywords="software engineer",
    location="New York, NY",
    remote_only=False,
    experience_level="mid_senior_level",  # see data/job_search_config.json -> linkedin.experience_levels
    job_type="full_time",                 # see data/job_search_config.json -> linkedin.job_types
    date_posted="past_week",              # any_time | past_month | past_week | past_24_hours
    max_results=25,
)

for job in jobs:
    print(job.title, job.company, job.location, job.url)
```

## Notes

- LinkedIn may rate-limit or block sustained automated traffic in either mode. Keep `max_results` modest and don't remove the client's built-in delay between paginated requests.
- Filter values (experience level, job type, date-posted codes) live in `data/job_search_config.json` under `linkedin`. Update that file if LinkedIn changes its filter codes — don't hardcode new values in the client.
- Returns a list of `JobPosting` objects (`clients/common.py`) with `title`, `company`, `location`, `url`, `job_id`, `posted_at` (guest mode only).
- Both LinkedIn endpoints are undocumented/unversioned for third-party use and can change without notice. If parsing starts returning zero results, check `_parse_guest_page` (guest mode) or `_parse_voyager_response` (authenticated mode) in `clients/linkedin_client.py` against the current response.
- The authenticated mode has not been verified against a live LinkedIn account in this environment (outbound network to linkedin.com is blocked here) — its request-building and response-parsing logic is covered by `tests/test_linkedin_client_authenticated.py` against fixtures, but confirm it against a real account before relying on it.
