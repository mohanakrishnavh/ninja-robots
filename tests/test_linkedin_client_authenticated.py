"""Dedicated eval/test suite for linkedin-job-search's authenticated mode.

Covers reading the LINKEDIN_LI_AT_COOKIE credential from the environment
(never hardcoded), the lazy CSRF-token bootstrap (fetched on first
search() call, not at construction time), and Voyager search response
parsing -- all against fixtures, no live network calls.
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


def test_credential_present_reports_authenticated_without_any_network_call(monkeypatch):
    """Constructing the client must not make a network call -- the CSRF
    token bootstrap is deferred until search() actually needs it."""
    monkeypatch.setenv(LI_AT_COOKIE_ENV_VAR, "fake-li-at-value")

    with patch("clients.linkedin_client.requests.Session.get") as mock_get:
        client = LinkedInJobClient()

    assert client.is_authenticated is True
    mock_get.assert_not_called()


def test_constructor_arg_overrides_env_var(monkeypatch):
    monkeypatch.setenv(LI_AT_COOKIE_ENV_VAR, "env-value")
    client = LinkedInJobClient(li_at_cookie="explicit-value")
    assert client._li_at_cookie == "explicit-value"


def test_first_search_call_fetches_and_caches_the_csrf_token(monkeypatch):
    monkeypatch.setenv(LI_AT_COOKIE_ENV_VAR, "fake-li-at-value")
    client = LinkedInJobClient()
    client.request_delay = 0

    feed_response = _fake_response(text="", cookies={"JSESSIONID": '"ajax:1234567890"'})
    empty_body = json.loads((FIXTURES / "linkedin_voyager_empty_response.json").read_text())

    with patch.object(
        client.session,
        "get",
        side_effect=[feed_response, _fake_response(json_body=empty_body)],
    ) as mock_get:
        client.search(keywords="engineer", max_results=1)

    assert client.session.headers["csrf-token"] == "ajax:1234567890"
    assert client.session.cookies.get("li_at") == "fake-li-at-value"
    assert client._session_ready is True

    # A second search reuses the cached token instead of re-fetching the feed page.
    with patch.object(
        client.session, "get", return_value=_fake_response(json_body=empty_body)
    ) as mock_get_second:
        client.search(keywords="engineer", max_results=1)

    called_urls = [call.args[0] for call in mock_get_second.call_args_list]
    assert client._config["feed_url"] not in called_urls


def test_missing_jsessionid_raises_clear_error_on_search(monkeypatch):
    monkeypatch.setenv(LI_AT_COOKIE_ENV_VAR, "expired-or-invalid")
    client = LinkedInJobClient()

    feed_response = _fake_response(text="", cookies={})
    with patch.object(client.session, "get", return_value=feed_response):
        with pytest.raises(RuntimeError):
            client.search(keywords="engineer", max_results=1)


def test_authenticated_search_parses_voyager_response(monkeypatch):
    monkeypatch.setenv(LI_AT_COOKIE_ENV_VAR, "fake-li-at-value")
    client = LinkedInJobClient()
    client.request_delay = 0

    feed_response = _fake_response(text="", cookies={"JSESSIONID": '"ajax:1234567890"'})
    search_body = json.loads((FIXTURES / "linkedin_voyager_search_response.json").read_text())
    empty_body = json.loads((FIXTURES / "linkedin_voyager_empty_response.json").read_text())

    with patch.object(
        client.session,
        "get",
        side_effect=[
            feed_response,
            _fake_response(json_body=search_body),
            _fake_response(json_body=empty_body),
        ],
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
    client = LinkedInJobClient()

    geo_body = json.loads((FIXTURES / "linkedin_typeahead_geo_response.json").read_text())
    with patch.object(client.session, "get", return_value=_fake_response(json_body=geo_body)):
        geo_id = client._resolve_geo_id("San Francisco Bay Area")

    assert geo_id == "103644278"
