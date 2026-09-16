"""Dedicated client for searching LinkedIn job postings.

Two modes, chosen automatically based on whether credentials are available:

- Guest (default, no credentials): calls LinkedIn's public, no-login
  "jobs-guest" search endpoint -- the same one an anonymous browser hits
  from the LinkedIn jobs search page.
- Authenticated (set LINKEDIN_LI_AT_COOKIE): searches as a logged-in user
  via LinkedIn's internal Voyager API, which the linkedin.com web app
  itself calls after login. This needs your account's `li_at` session
  cookie value (copy it from your browser's dev tools -> Application ->
  Cookies while logged into linkedin.com). Never hardcode this value --
  set it as the LINKEDIN_LI_AT_COOKIE environment variable instead. The
  CSRF token this mode needs is fetched lazily, on the first search()
  call, not when the client is constructed.

Both modes hit endpoints LinkedIn hasn't published or versioned for
third-party use. LinkedIn may change the markup/schema at any time, and
the authenticated mode in particular is automated use of a personal
account against LinkedIn's Terms of Service -- it can get that account
rate-limited or restricted, so use an account you're comfortable putting
at that risk and keep request volume low.
"""
from __future__ import annotations

import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .common import JobPosting, get_env_credential, load_platform_config

LI_AT_COOKIE_ENV_VAR = "LINKEDIN_LI_AT_COOKIE"


class LinkedInJobClient:
    """Searches LinkedIn job postings, as a guest or as an authenticated user."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        li_at_cookie: Optional[str] = None,
    ):
        self._config = load_platform_config("linkedin")
        self.session = session or requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; job-search-skill/1.0)"}
        )
        self.request_delay = self._config["default_request_delay_seconds"]

        self._li_at_cookie = li_at_cookie or get_env_credential(LI_AT_COOKIE_ENV_VAR)
        self._session_ready = False

    @property
    def is_authenticated(self) -> bool:
        """Whether an li_at credential is configured, so search() will use
        authenticated mode. The CSRF token itself is fetched lazily -- on
        the first search() call, not at construction time -- so this can
        be True before that network round trip has actually happened."""
        return bool(self._li_at_cookie)

    def _ensure_authenticated_session(self) -> None:
        """Attach the li_at cookie and derive the CSRF token LinkedIn's
        internal API requires on every request, by visiting the feed page
        the way a logged-in browser would right after authenticating.

        Called lazily from search() rather than __init__, so constructing
        a client with a credential configured doesn't spend a network
        round trip (or fail loudly on a bad cookie) until it's actually
        needed. Cached after the first successful call.
        """
        if self._session_ready:
            return

        self.session.cookies.set("li_at", self._li_at_cookie, domain=".linkedin.com")
        response = self.session.get(self._config["feed_url"], timeout=10)
        response.raise_for_status()

        jsessionid = response.cookies.get("JSESSIONID") or self.session.cookies.get("JSESSIONID")
        if not jsessionid:
            raise RuntimeError(
                f"LinkedIn did not return a JSESSIONID for the {LI_AT_COOKIE_ENV_VAR} "
                "cookie; it may be expired or invalid."
            )

        self.session.headers.update(
            {
                "csrf-token": jsessionid.strip('"'),
                "x-restli-protocol-version": "2.0.0",
                "x-li-lang": "en_US",
            }
        )
        self._session_ready = True

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
        linkedin.date_posted (default "any_time"). Uses the authenticated
        Voyager search when a valid li_at cookie was provided, otherwise
        falls back to the public guest search.
        """
        if self._li_at_cookie:
            self._ensure_authenticated_session()
            return self._search_authenticated(
                keywords, location, remote_only, experience_level, job_type, date_posted, max_results
            )
        return self._search_guest(
            keywords, location, remote_only, experience_level, job_type, date_posted, max_results
        )

    # -- Guest (public, unauthenticated) search --------------------------

    def _search_guest(
        self,
        keywords: str,
        location: str,
        remote_only: bool,
        experience_level: Optional[str],
        job_type: Optional[str],
        date_posted: str,
        max_results: int,
    ) -> list[JobPosting]:
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

            page_jobs = self._parse_guest_page(response.text)
            if not page_jobs:
                break

            results.extend(page_jobs)
            start += page_size
            time.sleep(self.request_delay)

        return results[:max_results]

    def _parse_guest_page(self, html_text: str) -> list[JobPosting]:
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

    # -- Authenticated (logged-in user, Voyager API) search ---------------

    def _search_authenticated(
        self,
        keywords: str,
        location: str,
        remote_only: bool,
        experience_level: Optional[str],
        job_type: Optional[str],
        date_posted: str,
        max_results: int,
    ) -> list[JobPosting]:
        geo_id = self._resolve_geo_id(location) if location else None
        page_size = self._config["page_size"]
        results: list[JobPosting] = []
        start = 0

        while len(results) < max_results:
            query = self._build_voyager_query(
                keywords, geo_id, remote_only, experience_level, job_type, date_posted
            )
            params = {
                "decorationId": self._config["voyager_decoration_id"],
                "q": "jobSearch",
                "query": query,
                "start": start,
                "count": page_size,
            }

            response = self.session.get(
                self._config["voyager_search_url"], params=params, timeout=10
            )
            response.raise_for_status()

            page_jobs = self._parse_voyager_response(response.json())
            if not page_jobs:
                break

            results.extend(page_jobs)
            start += page_size
            time.sleep(self.request_delay)

        return results[:max_results]

    def _build_voyager_query(
        self,
        keywords: str,
        geo_id: Optional[str],
        remote_only: bool,
        experience_level: Optional[str],
        job_type: Optional[str],
        date_posted: str,
    ) -> str:
        parts = [f"keywords:{keywords}"]
        if geo_id:
            parts.append(f"locationUnion:(geoId:{geo_id})")

        filters = []
        if remote_only:
            filters.append("workplaceType->List(2)")
        experience_code = self._config["experience_levels"].get(experience_level or "", "")
        if experience_code:
            filters.append(f"experience->List({experience_code})")
        job_type_code = self._config["job_types"].get(job_type or "", "")
        if job_type_code:
            filters.append(f"jobType->List({job_type_code})")
        date_range = self._config["date_posted"].get(date_posted, "")
        if date_range:
            filters.append(f"timePostedRange->List({date_range})")
        if filters:
            parts.append(f"selectedFilters:({','.join(filters)})")

        return f"(origin:JOB_SEARCH_PAGE_QUERY_EXPANSION,{','.join(parts)},spellCorrectionEnabled:true)"

    def _resolve_geo_id(self, location: str) -> Optional[str]:
        """Look up LinkedIn's internal geo ID for a free-text location string."""
        params = {"keywords": location, "origin": "jobs-search-box", "q": "type", "type": "GEO"}
        response = self.session.get(
            self._config["voyager_typeahead_url"], params=params, timeout=10
        )
        response.raise_for_status()

        data = response.json()
        elements = data.get("data", {}).get("elements") or data.get("elements") or []
        for element in elements:
            target_urn = element.get("targetUrn", "")
            if "geo:" in target_urn:
                return target_urn.split("geo:")[-1]
        return None

    def _parse_voyager_response(self, data: dict) -> list[JobPosting]:
        jobs: list[JobPosting] = []

        for item in data.get("included", []):
            item_type = item.get("$type", "")
            if "JobPosting" not in item_type:
                continue

            title = item.get("title")
            if isinstance(title, dict):
                title = title.get("text")
            if not title:
                continue

            company = ""
            company_details = item.get("companyDetails")
            if isinstance(company_details, dict):
                company_info = company_details.get("company")
                if isinstance(company_info, dict):
                    company = company_info.get("name", "")

            job_urn = item.get("entityUrn", "") or item.get("jobPostingUrn", "")
            job_id = job_urn.split(":")[-1] if job_urn else None
            url = f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id else ""

            jobs.append(
                JobPosting(
                    title=title,
                    company=company,
                    location=item.get("formattedLocation", "") or "",
                    url=url,
                    source="linkedin",
                    job_id=job_id,
                )
            )

        return jobs
