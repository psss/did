# coding: utf-8
""" Tests for the GitLab plugin """

import logging
import os

import pytest
from _pytest.logging import LogCaptureFixture

import did.base
import did.cli

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
        assert "Fetching more paginated data" in caplog.text
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
def test_gitlab_config_disabled_ssl_verify():
    """  Test ssl_verify disabled """
    did.base.Config(f"""
{CONFIG}
ssl_verify = False
""")
    did.cli.main(INTERVAL)
