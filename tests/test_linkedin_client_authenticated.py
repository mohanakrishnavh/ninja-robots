"""Dedicated eval/test suite for linkedin-job-search's authenticated mode.

Covers reading the LINKEDIN_LI_AT_COOKIE credential from the environment
(never hardcoded), the authenticated-session bootstrap, and Voyager search
response parsing -- all against fixtures, no live network calls.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clients.linkedin_client import LI_AT_COOKIE_ENV_VAR, LinkedInJobClient

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_response(json_body=None, text=None, cookies=None) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.cookies = cookies or {}
    if json_body is not None:
        response.json = MagicMock(return_value=json_body)
    if text is not None:
        response.text = text
    return response


def test_no_credential_falls_back_to_guest_mode(monkeypatch):
    monkeypatch.delenv(LI_AT_COOKIE_ENV_VAR, raising=False)
    client = LinkedInJobClient()
    assert client.is_authenticated is False


def test_reads_credential_from_env_var_not_hardcoded(monkeypatch):
    monkeypatch.setenv(LI_AT_COOKIE_ENV_VAR, "fake-li-at-value")
    feed_response = _fake_response(text="", cookies={"JSESSIONID": '"ajax:1234567890"'})

    with patch("clients.linkedin_client.requests.Session.get", return_value=feed_response):
        client = LinkedInJobClient()

    assert client.is_authenticated is True
    assert client.session.headers["csrf-token"] == "ajax:1234567890"
    assert client.session.cookies.get("li_at") == "fake-li-at-value"


def test_constructor_arg_overrides_env_var(monkeypatch):
    monkeypatch.setenv(LI_AT_COOKIE_ENV_VAR, "env-value")
    feed_response = _fake_response(text="", cookies={"JSESSIONID": '"ajax:9999"'})

    with patch("clients.linkedin_client.requests.Session.get", return_value=feed_response):
        client = LinkedInJobClient(li_at_cookie="explicit-value")

    assert client.session.cookies.get("li_at") == "explicit-value"


def test_missing_jsessionid_raises_clear_error(monkeypatch):
    monkeypatch.setenv(LI_AT_COOKIE_ENV_VAR, "expired-or-invalid")
    feed_response = _fake_response(text="", cookies={})

    with patch("clients.linkedin_client.requests.Session.get", return_value=feed_response):
        with pytest.raises(RuntimeError):
            LinkedInJobClient()


def test_authenticated_search_parses_voyager_response(monkeypatch):
    monkeypatch.setenv(LI_AT_COOKIE_ENV_VAR, "fake-li-at-value")
    feed_response = _fake_response(text="", cookies={"JSESSIONID": '"ajax:1234567890"'})

    search_body = json.loads((FIXTURES / "linkedin_voyager_search_response.json").read_text())
    empty_body = json.loads((FIXTURES / "linkedin_voyager_empty_response.json").read_text())

    with patch("clients.linkedin_client.requests.Session.get", return_value=feed_response):
        client = LinkedInJobClient()
    client.request_delay = 0

    with patch.object(
        client.session,
        "get",
        side_effect=[_fake_response(json_body=search_body), _fake_response(json_body=empty_body)],
    ):
        jobs = client.search(keywords="software engineer", max_results=5)

    assert len(jobs) == 2
    assert jobs[0].title == "Staff Software Engineer"
    assert jobs[0].company == "Hooli"
    assert jobs[0].location == "Remote"
    assert jobs[0].job_id == "9876543210"
    assert jobs[0].url == "https://www.linkedin.com/jobs/view/9876543210/"
    assert jobs[0].source == "linkedin"


def test_resolve_geo_id_parses_typeahead_response(monkeypatch):
    monkeypatch.setenv(LI_AT_COOKIE_ENV_VAR, "fake-li-at-value")
    feed_response = _fake_response(text="", cookies={"JSESSIONID": '"ajax:1234567890"'})

    with patch("clients.linkedin_client.requests.Session.get", return_value=feed_response):
        client = LinkedInJobClient()

    geo_body = json.loads((FIXTURES / "linkedin_typeahead_geo_response.json").read_text())
    with patch.object(client.session, "get", return_value=_fake_response(json_body=geo_body)):
        geo_id = client._resolve_geo_id("San Francisco Bay Area")

    assert geo_id == "103644278"
