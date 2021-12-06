# coding: utf-8
""" Tests for the git plugin """

import os

import pytest

import did.cli
import did.utils

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Prepare interval and config file with real path to our git repo
INTERVAL = "--since 2015-09-07 --until 2015-09-11"
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
GIT_PATH = os.path.realpath('{0}/../../'.format(SCRIPT_PATH))
CONFIG = """
[general]
email = "Petr Splichal" <psplicha@redhat.com>

[tools]
type = git
did = {0}
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Smoke
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_git_smoke():
    """ Git smoke """
    did.base.Config(CONFIG.format(GIT_PATH))
    did.cli.main(INTERVAL)


def test_git_verbosity():
    """ Brief git stats """
    did.base.Config(CONFIG.format(GIT_PATH))
    did.cli.main(INTERVAL + " --brief")
    did.cli.main(INTERVAL + " --verbose")


def test_git_format():
    """ Wiki format """
    did.base.Config(CONFIG.format(GIT_PATH))
    did.cli.main(INTERVAL + " --format text")
    did.cli.main(INTERVAL + " --format wiki")


def test_git_team():
    """ Team report """
    emails = " --email psplicha@redhat.com,cward@redhat.com"
    did.base.Config(CONFIG.format(GIT_PATH))
    did.cli.main(INTERVAL + emails)
    did.cli.main(INTERVAL + emails + "--total")
    did.cli.main(INTERVAL + emails + "--merge")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Content
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_git_regular():
    """ Simple git stats """
    did.base.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    assert any([
        "8a725af - Simplify git plugin tests" in stat
        for stat in stats])


def test_git_verbose():
    """ Verbose git stats """
    did.base.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main(INTERVAL + " --verbose")[0][0].stats[0].stats[0].stats
    assert any(["tests/plugins" in stat for stat in stats])


def test_git_nothing():
    """ No stats found """
    did.base.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main("--until 2015-01-01")[0][0].stats[0].stats[0].stats
    assert stats == []


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Errors
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_git_invalid():
    """ Invalid git repo """
    did.base.Config(CONFIG.format("/tmp"))
    try:
        did.cli.main(INTERVAL)
    except SystemExit:
        raise RuntimeError("Expected warning only")


def test_git_non_existent():
    """ Non-existent git repo """
    did.base.Config(CONFIG.format("i-do-not-exist"))
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)
