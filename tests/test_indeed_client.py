"""Dedicated eval/test suite for the indeed-job-search skill's client.

Uses fixture HTML instead of live network calls so results are deterministic
and don't depend on Indeed's markup being reachable or unchanged at test
time (see clients/indeed_client.py's module docstring for why live calls
are unreliable to depend on).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from clients.indeed_client import IndeedJobClient

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_response(html_text: str) -> MagicMock:
    response = MagicMock()
    response.text = html_text
    response.raise_for_status = MagicMock()
    return response


def test_search_parses_job_fields_from_search_results():
    client = IndeedJobClient()
    client.request_delay = 0

    search_page = (FIXTURES / "indeed_search_page.html").read_text()
    empty_page = (FIXTURES / "indeed_empty_page.html").read_text()

    with patch.object(
        client.session,
        "get",
        side_effect=[_fake_response(search_page), _fake_response(empty_page)],
    ):
        jobs = client.search(keywords="data analyst", location="Austin, TX", max_results=5)

    assert len(jobs) == 2

    first = jobs[0]
    assert first.title == "Data Analyst"
    assert first.company == "Initech"
    assert first.location == "Austin, TX"
    assert first.url == "https://www.indeed.com/rc/clk?jk=abc123"
    assert first.source == "indeed"
    assert first.job_id == "abc123"


def test_search_respects_max_results():
    client = IndeedJobClient()
    client.request_delay = 0

    search_page = (FIXTURES / "indeed_search_page.html").read_text()

    with patch.object(client.session, "get", return_value=_fake_response(search_page)):
        jobs = client.search(keywords="analyst", max_results=1)

    assert len(jobs) == 1


def test_search_stops_pagination_on_empty_page():
    client = IndeedJobClient()
    client.request_delay = 0

    empty_page = (FIXTURES / "indeed_empty_page.html").read_text()

    with patch.object(client.session, "get", return_value=_fake_response(empty_page)) as mock_get:
        jobs = client.search(keywords="nonexistent role", max_results=25)

    assert jobs == []
    assert mock_get.call_count == 1


def test_job_type_and_date_posted_map_to_config_params():
    client = IndeedJobClient()
    client.request_delay = 0

    empty_page = (FIXTURES / "indeed_empty_page.html").read_text()

    with patch.object(client.session, "get", return_value=_fake_response(empty_page)) as mock_get:
        client.search(
            keywords="analyst",
            job_type="full_time",
            date_posted="last_7",
            radius_miles=25,
            max_results=1,
        )

    params = mock_get.call_args.kwargs["params"]
    assert params["jt"] == "fulltime"
    assert params["fromage"] == 7
    assert params["radius"] == 25


def test_custom_country_domain_is_used_for_base_url_and_links():
    client = IndeedJobClient(country_domain="uk.indeed.com")
    assert client.base_url == "https://uk.indeed.com/jobs"
