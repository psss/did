# coding: utf-8
""" Tests for the GitLab plugin """

import datetime
import logging
import os
from types import SimpleNamespace

import pytest
from _pytest.logging import LogCaptureFixture

import did.base
import did.cli
import did.plugins.gitlab

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2023-01-20 --until 2023-01-20"
APPROVED_INTERVAL = "--since 2021-04-08 --until 2021-04-09"
PAGINATED_INTERVAL = "--since 2025-01-01 --until 2025-02-28"

CONFIG_NOTOKEN = """
[general]
email = "Petr Splichal" <psplicha@redhat.com>

[gitlab]
type = gitlab
url = https://gitlab.com
login = did.tester
"""

CONFIG = f"""
{CONFIG_NOTOKEN}
token = {os.getenv(key="GITLAB_TOKEN", default="NoTokenSpecified")}
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@pytest.mark.skipif("GITLAB_TOKEN" not in os.environ,
                    reason="No GITLAB_TOKEN environment variable found")
def test_gitlab_issues_created():
    """ Created issues """
    did.base.Config(CONFIG)
    option = "--gitlab-issues-created "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[0].stats
    assert any(
        "did.tester/test-project#003 - the readme is almost empty"
        in str(stat) for stat in stats)


@pytest.mark.skipif("GITLAB_TOKEN" not in os.environ,
                    reason="No GITLAB_TOKEN environment variable found")
def test_gitlab_issues_commented():
    """ Commented issues """
    did.base.Config(CONFIG)
    option = "--gitlab-issues-commented "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[1].stats
    assert any(
        "did.tester/test-project#003 - the readme is almost empty"
        in str(stat) for stat in stats)


@pytest.mark.skipif("GITLAB_TOKEN" not in os.environ,
                    reason="No GITLAB_TOKEN environment variable found")
def test_gitlab_issues_closed():
    """ Closed issues in markdown format """
    did.base.Config(CONFIG)
    option = "--gitlab-issues-closed --format=markdown "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[2].stats
    assert any("[did.tester/test-project#3]" in str(stat) for stat in stats)


@pytest.mark.skipif("GITLAB_TOKEN" not in os.environ,
                    reason="No GITLAB_TOKEN environment variable found")
def test_gitlab_merge_requests_created():
    """ Created merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-created "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[3].stats
    assert any(
        "did.tester/test-project#004 - Update README.md" in str(stat)
        for stat in stats)


@pytest.mark.skipif("GITLAB_TOKEN" not in os.environ,
                    reason="No GITLAB_TOKEN environment variable found")
def test_gitlab_merge_requests_commented():
    """ Commented merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-commented "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[4].stats
    assert any(
        "did.tester/test-project#004 - Update README.md" in str(stat)
        for stat in stats)


@pytest.mark.skipif("GITLAB_TOKEN" not in os.environ,
                    reason="No GITLAB_TOKEN environment variable found")
def test_gitlab_paginated_merge_requests_commented(caplog: LogCaptureFixture):
    """ Approved merge requests """
    did.base.Config(CONFIG.replace("did.tester", "sandrobonazzola"))
    option = "--gitlab-merge-requests-commented "
    with caplog.at_level(logging.DEBUG, logger=did.base.log.name):
        stats = did.cli.main(option + PAGINATED_INTERVAL)[0][0].stats[0].stats[4].stats
        assert "Fetching " in caplog.text
    assert any(
        "CentOS/automotive/src/automotive-image-builder#220" in str(stat)
        for stat in stats)


@pytest.mark.skipif("GITLAB_TOKEN" not in os.environ,
                    reason="No GITLAB_TOKEN environment variable found")
def test_gitlab_merge_requests_closed():
    """ Closed merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-closed "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[6].stats
    assert any(
        "did.tester/test-project#004 - Update README.md" in str(stat)
        for stat in stats)


@pytest.mark.skipif("GITLAB_TOKEN" not in os.environ,
                    reason="No GITLAB_TOKEN environment variable found")
def test_gitlab_merge_requests_approved():
    """ Approved merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-approved "
    stats = did.cli.main(
        option + APPROVED_INTERVAL)[0][0].stats[0].stats[5].stats
    assert any(
        "did.tester/test-project#003 - Use a nice complete" in str(stat)
        for stat in stats)


def test_gitlab_missing_token(caplog: LogCaptureFixture):
    """ Missing token """
    did.base.Config(CONFIG_NOTOKEN)
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Skipping section gitlab due to error: No GitLab token" in caplog.text


def test_gitlab_invalid_token(caplog: LogCaptureFixture):
    """ Invalid token """
    did.base.Config(CONFIG_NOTOKEN + "\ntoken = bad-token")
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Unable to access" in caplog.text


def test_gitlab_missing_url(caplog: LogCaptureFixture):
    """ Missing url """
    did.base.Config(CONFIG.replace("url = https://gitlab.com\n", ""))
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Skipping section gitlab due to error: No GitLab url set" in caplog.text


def test_gitlab_wrong_url(caplog: LogCaptureFixture):
    """ Wrong url """
    did.base.Config(
        CONFIG.replace("url = https://gitlab.com\n", "url = https://localhost\n")
        )
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Unable to connect" in caplog.text


def test_gitlab_config_invaliad_ssl_verify(caplog: LogCaptureFixture):
    """  Test ssl_verify with wrong bool value """
    did.base.Config(f"""
{CONFIG}
ssl_verify = ss
""")
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Invalid ssl_verify option for GitLab" in caplog.text


@pytest.mark.skipif("GITLAB_TOKEN" not in os.environ,
                    reason="No GITLAB_TOKEN environment variable found")
def test_gitlab_merge_requests_merged():
    """
    Merged merge requests.

    Note: GITLAB_TOKEN must be for did.tester user to match test
    data. The global merge_requests API only returns MRs visible to
    the token owner.
    """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-merged "
    # Note: The stats list index is 7 for MergeRequestsMerged
    # MR #4 was merged on 2023-01-20 at 14:14:01
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[7].stats
    assert any(
        "did.tester/test-project#004" in str(stat) and "Update README.md" in str(stat)
        for stat in stats)


@pytest.mark.skipif("GITLAB_TOKEN" not in os.environ,
                    reason="No GITLAB_TOKEN environment variable found")
def test_gitlab_config_disabled_ssl_verify():
    """  Test ssl_verify disabled """
    did.base.Config(f"""
{CONFIG}
ssl_verify = False
""")
    did.cli.main(INTERVAL)


class FakeResponse:

    def __init__(self, payload, links=None):
        self.payload = payload
        self.links = links or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


class FakeFuture:

    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    def result(self):
        if self.error is not None:
            raise self.error
        return self.value


class FakeExecutor:

    def __init__(self, max_workers):
        self.max_workers = max_workers
        self.futures = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def submit(self, function, *args, **kwargs):
        try:
            future = FakeFuture(function(*args, **kwargs))
        except Exception as error:
            future = FakeFuture(error=error)
        self.futures.append(future)
        return future


def test_gitlab_api_list_preserves_page_order(monkeypatch):
    """ Pages fetched out of order are assembled in correct order """
    gitlab = did.plugins.gitlab.GitLab("https://gitlab.example.com", "token")
    first_page = FakeResponse(
        payload=[
            {'created_at': '2023-01-05T00:00:00Z', 'id': 1},
            {'created_at': '2023-01-04T00:00:00Z', 'id': 2},
            ],
        links={
            'next': {'url': 'https://gitlab.example.com/api/v4/events?page=2'},
            'last': {'url': 'https://gitlab.example.com/api/v4/events?page=3'},
            })
    later_pages = {
        2: FakeResponse([
            {'created_at': '2023-01-03T00:00:00Z', 'id': 3},
            {'created_at': '2023-01-02T00:00:00Z', 'id': 4},
            ]),
        3: FakeResponse([
            {'created_at': '2023-01-01T00:00:00Z', 'id': 5},
            ]),
        }

    def fake_get_gitlab_api(endpoint, params=None):
        assert endpoint == 'events'
        assert params is None
        return first_page

    def fake_get_gitlab_api_raw(url, params=None):
        del params
        page = int(url.split("page=")[1])
        return later_pages[page]

    monkeypatch.setattr(gitlab, "_get_gitlab_api", fake_get_gitlab_api)
    monkeypatch.setattr(gitlab, "_get_gitlab_api_raw", fake_get_gitlab_api_raw)
    monkeypatch.setattr(did.plugins.gitlab, "ThreadPoolExecutor", FakeExecutor)
    monkeypatch.setattr(
        did.plugins.gitlab,
        "as_completed",
        lambda futures: reversed(list(futures)))

    results = gitlab._get_gitlab_api_list(
        'events',
        since=SimpleNamespace(date=datetime.date(2023, 1, 2)),
        get_all_results=True)

    assert [item['id'] for item in results] == [1, 2, 3, 4]


def test_gitlab_api_list_wraps_page_fetch_errors(monkeypatch):
    """ Thread fetch errors are wrapped in ReportError """
    gitlab = did.plugins.gitlab.GitLab("https://gitlab.example.com", "token")
    first_page = FakeResponse(
        payload=[{'created_at': '2023-01-05T00:00:00Z', 'id': 1}],
        links={
            'next': {'url': 'https://gitlab.example.com/api/v4/events?page=2'},
            'last': {'url': 'https://gitlab.example.com/api/v4/events?page=2'},
            })

    def fake_get_gitlab_api(endpoint, params=None):
        assert endpoint == 'events'
        assert params is None
        return first_page

    def fake_get_gitlab_api_raw(url, params=None):
        del url, params
        raise RuntimeError("boom")

    monkeypatch.setattr(gitlab, "_get_gitlab_api", fake_get_gitlab_api)
    monkeypatch.setattr(gitlab, "_get_gitlab_api_raw", fake_get_gitlab_api_raw)
    monkeypatch.setattr(did.plugins.gitlab, "ThreadPoolExecutor", FakeExecutor)
    monkeypatch.setattr(
        did.plugins.gitlab,
        "as_completed",
        lambda futures: list(futures))

    with pytest.raises(did.base.ReportError, match="Unable to fetch page 2"):
        gitlab._get_gitlab_api_list('events', get_all_results=True)


def test_gitlab_api_list_falls_back_to_next_links(monkeypatch):
    """ Sequential next-link fallback when last header is missing """
    gitlab = did.plugins.gitlab.GitLab("https://gitlab.example.com", "token")
    first_page = FakeResponse(
        payload=[{'created_at': '2023-01-05T00:00:00Z', 'id': 1}],
        links={
            'next': {'url': 'https://gitlab.example.com/api/v4/events?page=2'},
            })
    later_pages = {
        2: FakeResponse(
            [],
            links={
                'next': {
                    'url': 'https://gitlab.example.com/api/v4/events?page=3'}
                }),
        3: FakeResponse([
            {'created_at': '2023-01-04T00:00:00Z', 'id': 2},
            {'created_at': '2023-01-01T00:00:00Z', 'id': 3},
            ]),
        }

    def fake_get_gitlab_api(endpoint, params=None):
        assert endpoint == 'events'
        assert params is None
        return first_page

    def fake_get_gitlab_api_raw(url, params=None):
        del params
        page = int(url.split("page=")[1])
        return later_pages[page]

    monkeypatch.setattr(gitlab, "_get_gitlab_api", fake_get_gitlab_api)
    monkeypatch.setattr(gitlab, "_get_gitlab_api_raw", fake_get_gitlab_api_raw)

    results = gitlab._get_gitlab_api_list(
        'events',
        since=SimpleNamespace(date=datetime.date(2023, 1, 2)),
        get_all_results=True)

    assert [item['id'] for item in results] == [1, 2]


