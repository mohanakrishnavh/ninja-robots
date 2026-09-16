"""Dedicated eval/test suite for indeed-job-search's Publisher API mode.

Covers reading the INDEED_PUBLISHER_ID credential from the environment
(never hardcoded) and Publisher API response parsing -- all against
fixtures, no live network calls.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from clients.indeed_client import PUBLISHER_ID_ENV_VAR, IndeedJobClient

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_response(json_body: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=json_body)
    return response


def test_no_credential_falls_back_to_public_mode(monkeypatch):
    monkeypatch.delenv(PUBLISHER_ID_ENV_VAR, raising=False)
    client = IndeedJobClient()
    assert client.is_authenticated is False


def test_reads_credential_from_env_var_not_hardcoded(monkeypatch):
    monkeypatch.setenv(PUBLISHER_ID_ENV_VAR, "fake-publisher-id")
    client = IndeedJobClient()
    assert client.is_authenticated is True
    assert client._publisher_id == "fake-publisher-id"


def test_constructor_arg_overrides_env_var(monkeypatch):
    monkeypatch.setenv(PUBLISHER_ID_ENV_VAR, "env-value")
    client = IndeedJobClient(publisher_id="explicit-value")
    assert client._publisher_id == "explicit-value"


def test_authenticated_search_parses_publisher_api_response(monkeypatch):
    monkeypatch.setenv(PUBLISHER_ID_ENV_VAR, "fake-publisher-id")
    client = IndeedJobClient()
    client.request_delay = 0

    search_body = json.loads((FIXTURES / "indeed_publisher_api_response.json").read_text())
    empty_body = json.loads((FIXTURES / "indeed_publisher_api_empty_response.json").read_text())

    with patch.object(
        client.session,
        "get",
        side_effect=[_fake_response(search_body), _fake_response(empty_body)],
    ):
        jobs = client.search(keywords="data analyst", location="Austin, TX", max_results=5)

    assert len(jobs) == 2
    assert jobs[0].title == "Senior Data Analyst"
    assert jobs[0].company == "Initech"
    assert jobs[0].location == "Austin, TX"
    assert jobs[0].job_id == "abc123"
    assert jobs[0].source == "indeed"
    assert jobs[0].description == "We are looking for a senior data analyst..."


def test_authenticated_search_sends_publisher_id_param(monkeypatch):
    monkeypatch.setenv(PUBLISHER_ID_ENV_VAR, "fake-publisher-id")
    client = IndeedJobClient()
    client.request_delay = 0

    empty_body = json.loads((FIXTURES / "indeed_publisher_api_empty_response.json").read_text())

    with patch.object(client.session, "get", return_value=_fake_response(empty_body)) as mock_get:
        client.search(keywords="analyst", max_results=1)

    params = mock_get.call_args.kwargs["params"]
    assert params["publisher"] == "fake-publisher-id"
    assert params["format"] == "json"
