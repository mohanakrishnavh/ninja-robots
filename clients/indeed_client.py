"""Dedicated client for searching public Indeed job postings.

Scrapes Indeed's public search results page — no login or API key needed.
Indeed changes its markup fairly often and may show CAPTCHAs to automated
traffic, so treat parsing as best-effort and keep request volume low.
"""
from __future__ import annotations

import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .common import JobPosting, load_platform_config


class IndeedJobClient:
    """Searches Indeed's public job listings."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        country_domain: Optional[str] = None,
    ):
        self._config = load_platform_config("indeed")
        self.session = session or requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; job-search-skill/1.0)"}
        )
        self.domain = country_domain or self._config["default_country_domain"]
        self.base_url = f"https://{self.domain}/jobs"
        self.request_delay = self._config["default_request_delay_seconds"]

    def search(
        self,
        keywords: str,
        location: str = "",
        remote_only: bool = False,
        job_type: Optional[str] = None,
        date_posted: str = "any_time",
        radius_miles: Optional[int] = None,
        max_results: int = 25,
    ) -> list[JobPosting]:
        """Search Indeed job postings and return up to max_results normalized postings.

        job_type accepts a key from data/job_search_config.json's
        indeed.job_types. date_posted accepts a key from
        indeed.date_posted_days (default "any_time").
        """
        page_size = self._config["page_size"]
        results: list[JobPosting] = []
        start = 0

        while len(results) < max_results:
            params = {"q": keywords, "l": "Remote" if remote_only else location, "start": start}
            if job_type:
                params["jt"] = self._config["job_types"].get(job_type, "")
            if radius_miles is not None:
                params["radius"] = radius_miles
            days = self._config["date_posted_days"].get(date_posted)
            if days:
                params["fromage"] = days

            response = self.session.get(self.base_url, params=params, timeout=10)
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

        for card in soup.select("div.job_seen_beacon, td.resultContent"):
            link_el = card.select_one("h2.jobTitle a")
            title_el = card.select_one("h2.jobTitle span[title]") or (
                link_el.select_one("span") if link_el else None
            )
            if not title_el or not link_el:
                continue

            company_el = card.select_one("span[data-testid='company-name']")
            location_el = card.select_one("div[data-testid='text-location']")
            job_id = link_el.get("data-jk") or (link_el.get("id") or "").replace("job_", "")
            href = link_el.get("href", "")
            url = href if href.startswith("http") else f"https://{self.domain}{href}"

            jobs.append(
                JobPosting(
                    title=title_el.get_text(strip=True),
                    company=company_el.get_text(strip=True) if company_el else "",
                    location=location_el.get_text(strip=True) if location_el else "",
                    url=url,
                    source="indeed",
                    job_id=job_id or None,
                )
            )

        return jobs
