# coding: utf-8
""" Tests for the GitLab plugin """

from __future__ import unicode_literals, absolute_import

import pytest
import did.cli
import did.base
import time


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2017-05-24 --until 2017-05-26"

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

def teardown_function(function):
    time.sleep(7)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_gitlab_issues_created():
    """ Created issues """
    did.base.Config(CONFIG)
    option = "--gitlab-issues-created "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[0].stats
    assert any([
        "did.tester/test-project#001 - the readme is almost empty" in unicode(stat) for stat in stats])

def test_gitlab_issues_commented():
    """ Commented issues """
    did.base.Config(CONFIG)
    option = "--gitlab-issues-commented "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[1].stats
    assert any([
        "did.tester/test-project#001 - the readme is almost empty" in unicode(stat) for stat in stats])

def test_gitlab_issues_closed():
    """ Closed issues """
    did.base.Config(CONFIG)
    option = "--gitlab-issues-closed "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[2].stats
    assert any([
        "did.tester/test-project#001 - the readme is almost empty" in unicode(stat) for stat in stats])

def test_gitlab_merge_requests_created():
    """ Created merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-created "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[3].stats
    assert any([
        "did.tester/test-project#001 - Update README.md" in unicode(stat)
        for stat in stats])

def test_gitlab_merge_requests_commented():
    """ Commentsd merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-commented "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[4].stats
    assert any([
        "did.tester/test-project#001 - Update README.md" in unicode(stat)
        for stat in stats])

def test_gitlab_merge_requests_closed():
    """ Closed merge requests """
    did.base.Config(CONFIG)
    option = "--gitlab-merge-requests-closed "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[5].stats
    assert any([
        "did.tester/test-project#001 - Update README.md" in unicode(stat)
        for stat in stats])

def test_github_invalid_token():
    """ Invalid token """
    did.base.Config(CONFIG_NOTOKEN)
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)
