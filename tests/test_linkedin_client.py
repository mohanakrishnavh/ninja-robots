"""Dedicated eval/test suite for the linkedin-job-search skill's client.

Uses fixture HTML instead of live network calls so results are deterministic
and don't depend on LinkedIn's markup being reachable or unchanged at test
time (see clients/linkedin_client.py's module docstring for why live calls
are unreliable to depend on).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from clients.linkedin_client import LinkedInJobClient

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_response(html_text: str) -> MagicMock:
    response = MagicMock()
    response.text = html_text
    response.raise_for_status = MagicMock()
    return response


def test_search_parses_job_fields_from_search_results():
    client = LinkedInJobClient()
    client.request_delay = 0

    search_page = (FIXTURES / "linkedin_search_page.html").read_text()
    empty_page = (FIXTURES / "linkedin_empty_page.html").read_text()

    with patch.object(
        client.session,
        "get",
        side_effect=[_fake_response(search_page), _fake_response(empty_page)],
    ):
        jobs = client.search(keywords="software engineer", location="Remote", max_results=5)

    assert len(jobs) == 2

    first = jobs[0]
    assert first.title == "Software Engineer"
    assert first.company == "Acme Corp"
    assert first.location == "Remote"
    assert first.url == "https://www.linkedin.com/jobs/view/software-engineer-at-acme-1234567"
    assert first.source == "linkedin"
    assert first.job_id == "1234567"
    assert first.posted_at == "2024-05-01"


def test_search_respects_max_results():
    client = LinkedInJobClient()
    client.request_delay = 0

    search_page = (FIXTURES / "linkedin_search_page.html").read_text()

    with patch.object(client.session, "get", return_value=_fake_response(search_page)):
        jobs = client.search(keywords="engineer", max_results=1)

    assert len(jobs) == 1


def test_search_stops_pagination_on_empty_page():
    client = LinkedInJobClient()
    client.request_delay = 0

    empty_page = (FIXTURES / "linkedin_empty_page.html").read_text()

    with patch.object(client.session, "get", return_value=_fake_response(empty_page)) as mock_get:
        jobs = client.search(keywords="nonexistent role", max_results=25)

    assert jobs == []
    assert mock_get.call_count == 1


def test_experience_level_and_job_type_map_to_config_codes():
    client = LinkedInJobClient()
    client.request_delay = 0

    empty_page = (FIXTURES / "linkedin_empty_page.html").read_text()

    with patch.object(client.session, "get", return_value=_fake_response(empty_page)) as mock_get:
        client.search(
            keywords="engineer",
            experience_level="mid_senior_level",
            job_type="full_time",
            date_posted="past_week",
            max_results=1,
        )

    params = mock_get.call_args.kwargs["params"]
    assert params["f_E"] == "4"
    assert params["f_JT"] == "F"
    assert params["f_TPR"] == "r604800"
