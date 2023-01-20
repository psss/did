# coding: utf-8
""" Tests for the GitLab plugin """

import pytest

import did.base
import did.cli

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2023-01-20 --until 2023-01-20"
APPROVED_INTERVAL = "--since 2021-04-08 --until 2021-04-09"

CONFIG_NOTOKEN = """
[general]
email = "Petr Splichal" <psplicha@redhat.com>

[gitlab]
type = gitlab
url = https://gitlab.com
login = did.tester
"""

CONFIG = CONFIG_NOTOKEN + """
token = vh1tNyke5KzWCynzyAKt
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_gitlab_issues_created():
    """ Created issues """
    did.base.Config(CONFIG)
    option = "--gitlab-issues-created "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[0].stats
    assert any([
        "did.tester/test-project#003 - the readme is almost empty"
        in str(stat) for stat in stats])


def test_gitlab_issues_commented():
    """ Commented issues """
    did.base.Config(CONFIG)
    option = "--gitlab-issues-commented "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[1].stats
    assert any([
        "did.tester/test-project#003 - the readme is almost empty"
        in str(stat) for stat in stats])


def test_gitlab_issues_closed():
    """ Closed issues """
    did.base.Config(CONFIG)
    option = "--gitlab-issues-closed "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[2].stats
    assert any([
        "did.tester/test-project#003 - the readme is almost empty"
        in str(stat) for stat in stats])


def test_gitlab_merge_requests_created():
    """ Created merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-created "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[3].stats
    assert any([
        "did.tester/test-project#004 - Update README.md" in str(stat)
        for stat in stats])


def test_gitlab_merge_requests_commented():
    """ Commented merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-commented "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[4].stats
    assert any([
        "did.tester/test-project#004 - Update README.md" in str(stat)
        for stat in stats])


def test_gitlab_merge_requests_closed():
    """ Closed merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-closed "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[6].stats
    assert any([
        "did.tester/test-project#004 - Update README.md" in str(stat)
        for stat in stats])


def test_gitlab_merge_requests_approved():
    """ Approved merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-approved "
    stats = did.cli.main(
        option + APPROVED_INTERVAL)[0][0].stats[0].stats[5].stats
    assert any([
        "did.tester/test-project#003 - Use a nice complete" in str(stat)
        for stat in stats])


def test_github_invalid_token():
    """ Invalid token """
    did.base.Config(CONFIG_NOTOKEN)
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)
