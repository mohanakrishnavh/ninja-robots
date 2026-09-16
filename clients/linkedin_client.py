"""Dedicated client for searching public LinkedIn job postings.

Uses LinkedIn's public, no-login "jobs-guest" search endpoint — the same
one an anonymous browser hits from the LinkedIn jobs search page. LinkedIn
may rate-limit or block sustained automated traffic, so keep result counts
modest and don't remove the delay between paginated requests.
"""
from __future__ import annotations

import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .common import JobPosting, load_platform_config


class LinkedInJobClient:
    """Searches LinkedIn's public job listings."""

    def __init__(self, session: Optional[requests.Session] = None):
        self._config = load_platform_config("linkedin")
        self.session = session or requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; job-search-skill/1.0)"}
        )
        self.request_delay = self._config["default_request_delay_seconds"]

    def search(
        self,
        keywords: str,
        location: str = "",
        remote_only: bool = False,
        experience_level: Optional[str] = None,
        job_type: Optional[str] = None,
        date_posted: str = "any_time",
        max_results: int = 25,
    ) -> list[JobPosting]:
        """Search LinkedIn job postings and return up to max_results normalized postings.

        experience_level and job_type accept the keys defined in
        data/job_search_config.json under linkedin.experience_levels /
        linkedin.job_types. date_posted accepts a key from
        linkedin.date_posted (default "any_time").
        """
        page_size = self._config["page_size"]
        results: list[JobPosting] = []
        start = 0

        while len(results) < max_results:
            params = {"keywords": keywords, "location": location, "start": start}
            if remote_only:
                params["f_WT"] = "2"
            if experience_level:
                params["f_E"] = self._config["experience_levels"].get(experience_level, "")
            if job_type:
                params["f_JT"] = self._config["job_types"].get(job_type, "")
            date_range = self._config["date_posted"].get(date_posted, "")
            if date_range:
                params["f_TPR"] = date_range

            response = self.session.get(
                self._config["base_search_url"], params=params, timeout=10
            )
            response.raise_for_status()

            page_jobs = self._parse_page(response.text)
            if not page_jobs:
                break

            results.extend(page_jobs)
            start += page_size
            time.sleep(self.request_delay)

        return results[:max_results]

    def _parse_page(self, html_text: str) -> list[JobPosting]:
        soup = BeautifulSoup(html_text, "html.parser")
        jobs: list[JobPosting] = []

        for card in soup.select("li"):
            title_el = card.select_one("h3.base-search-card__title")
            link_el = card.select_one("a.base-card__full-link")
            if not title_el or not link_el:
                continue

            company_el = card.select_one("h4.base-search-card__subtitle")
            location_el = card.select_one("span.job-search-card__location")
            time_el = card.select_one("time")
            url = link_el.get("href", "").split("?")[0]
            job_id = url.rstrip("/").split("-")[-1] if url else None

            jobs.append(
                JobPosting(
                    title=title_el.get_text(strip=True),
                    company=company_el.get_text(strip=True) if company_el else "",
                    location=location_el.get_text(strip=True) if location_el else "",
                    url=url,
                    source="linkedin",
                    job_id=job_id,
                    posted_at=time_el.get("datetime") if time_el else None,
                )
            )

        return jobs
