# coding: utf-8
""" Tests for the GitHub plugin """

import os
import time
from tempfile import NamedTemporaryFile

import pytest

import did.base
import did.cli

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2015-09-05 --until 2015-09-06"

CONFIG = """
[general]
email = "Petr Splichal" <psplicha@redhat.com>

[gh]
type = github
url = https://api.github.com/
login = psss
"""

# GitHub has quite strict limits for unauthenticated searches
# https://developer.github.com/v3/search/#rate-limit
# Let's have a short nap after each test


def teardown_function(function):
    time.sleep(7)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_github_issues_created():
    """ Created issues """
    did.base.Config(CONFIG)
    option = "--gh-issues-created "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[0].stats
    assert any([
        "psss/did#017 - What did you do" in str(stat) for stat in stats])


def test_github_issues_closed():
    """ Closed issues """
    did.base.Config(CONFIG)
    option = "--gh-issues-closed "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[2].stats
    assert any([
        "psss/did#017 - What did you do" in str(stat) for stat in stats])


def test_github_pull_requests_created():
    """ Created pull requests """
    did.base.Config("[gh]\ntype = github\nurl = https://api.github.com/")
    option = "--gh-pull-requests-created "
    INTERVAL = "--since 2016-10-26 --until 2016-10-26"
    EMAIL = " --email mfrodl@redhat.com"
    stats = did.cli.main(
        option + INTERVAL + EMAIL)[0][0].stats[0].stats[3].stats
    assert any([
        "psss/did#112 - Fixed test for Trac plugin" in str(stat)
        for stat in stats])


def test_github_pull_requests_closed():
    """ Closed pull requests """
    did.base.Config(CONFIG)
    option = "--gh-pull-requests-closed "
    INTERVAL = "--since 2015-09-22 --until 2015-09-22"
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[5].stats
    assert any([
        "psss/did#037 - Skip CI users" in str(stat) for stat in stats])


def test_github_pull_requests_reviewed():
    """ Reviewed pull requests """
    did.base.Config(CONFIG.replace('psss', 'evgeni'))
    option = "--gh-pull-requests-reviewed "
    INTERVAL = "--since 2017-02-22 --until 2017-02-23"
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[6].stats
    assert any(["Katello/katello-client-bootstrap#164" in str(stat)
                for stat in stats])


def test_github_pull_requests_commented():
    """ Commented pull requests """
    did.base.Config(CONFIG)
    option = "--gh-pull-requests-commented "
    INTERVAL = "--since 2023-01-10 --until 2023-01-23"
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[4].stats
    for stat in stats:
        print(stat)
    assert any([
        "psss/did#285 - Fix error when building SRPM in copr"
        in str(stat) for stat in stats])


def test_github_issues_commented():
    """ Commented issues """
    did.base.Config(CONFIG)
    option = "--gh-issues-commented "
    INTERVAL = "--since 2023-01-10 --until 2023-01-23"
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[1].stats
    assert any([
        "teemtee/tmt#1788 - Allow modification of imported plans"
        in str(stat) for stat in stats])


def test_github_invalid_token():
    """ Invalid token """
    did.base.Config(CONFIG + "\ntoken = bad-token")
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)


def test_github_missing_url():
    """ Missing url """
    did.base.Config("[gh]\ntype = github")
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)


def test_github_unicode():
    """ Created issues with Unicode characters """
    INTERVAL = "--since 2016-02-23 --until 2016-02-23"
    EMAIL = " --email hasys@example.org"
    did.base.Config("[gh]\ntype = github\nurl = https://api.github.com/")
    option = "--gh-pull-requests-created "
    stats = did.cli.main(
        option + INTERVAL + EMAIL)[0][0].stats[0].stats[3].stats
    assert any([
        "Boundary events lose it’s documentation" in str(stat)
        for stat in stats])


@pytest.mark.skipif("GITHUB_TOKEN" not in os.environ,
                    reason="No GITHUB_TOKEN environment variable found")
def test_github_issues_created_with_token_file():
    """ Created issues (config with token_file)"""
    token = os.getenv(key="GITHUB_TOKEN")
    with NamedTemporaryFile(mode="w+", encoding="utf-8") as file_handle:
        file_handle.writelines(token)
        file_handle.flush()
        config = CONFIG + f"\ntoken_file = {file_handle.name}"
        did.base.Config(config)
        option = "--gh-issues-created "
        stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[0].stats
        assert any([
            "psss/did#017 - What did you do" in str(stat) for stat in stats])
