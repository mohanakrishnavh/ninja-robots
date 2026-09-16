---
name: linkedin-job-search
description: Search public LinkedIn job postings by keywords, location, and filters (remote, experience level, job type, date posted). Use when the user wants to find or search jobs on LinkedIn.
---

# LinkedIn Job Search

Use `clients/linkedin_client.py`'s `LinkedInJobClient` to search LinkedIn's public job listings.

## Usage

```python
from clients.linkedin_client import LinkedInJobClient

client = LinkedInJobClient()
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

- No LinkedIn login or API key is required — this calls LinkedIn's public "jobs-guest" search endpoint, the same one an anonymous visitor's browser hits.
- LinkedIn may rate-limit or block sustained automated traffic. Keep `max_results` modest and don't remove the client's built-in delay between paginated requests.
- Filter values (experience level, job type, date-posted codes) live in `data/job_search_config.json` under `linkedin`. Update that file if LinkedIn changes its filter codes — don't hardcode new values in the client.
- Returns a list of `JobPosting` objects (`clients/common.py`) with `title`, `company`, `location`, `url`, `job_id`, `posted_at`.
- Site markup can change over time; if parsing starts returning zero results, check `_parse_page` selectors in `clients/linkedin_client.py` against the current page HTML.
