---
name: indeed-job-search
description: Search public Indeed job postings by keywords, location, and filters (remote, job type, date posted, radius). Use when the user wants to find or search jobs on Indeed.
---

# Indeed Job Search

Use `clients/indeed_client.py`'s `IndeedJobClient` to search Indeed's public job listings.

## Usage

```python
from clients.indeed_client import IndeedJobClient

client = IndeedJobClient()
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

- No Indeed login or API key is required — this scrapes Indeed's public search results page.
- Indeed changes its markup fairly often and may show CAPTCHAs to automated traffic. Keep `max_results` modest and don't remove the client's built-in delay between paginated requests.
- To search a different country's Indeed site, pass `country_domain="uk.indeed.com"` (etc.) when constructing `IndeedJobClient`.
- Filter values (job types, date-posted windows) live in `data/job_search_config.json` under `indeed`. Update that file if Indeed changes its filter parameters — don't hardcode new values in the client.
- Returns a list of `JobPosting` objects (`clients/common.py`) with `title`, `company`, `location`, `url`, `job_id`.
- Site markup can change over time; if parsing starts returning zero results, check `_parse_page` selectors in `clients/indeed_client.py` against the current page HTML.
