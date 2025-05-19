# coding: utf-8
""" Tests for the git plugin """

import logging
import os

from _pytest.logging import LogCaptureFixture

import did.cli
import did.utils

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Prepare interval and config file with real path to our git repo
INTERVAL = "--since 2015-09-07 --until 2015-09-11"
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
GIT_PATH = os.path.realpath(f'{SCRIPT_PATH}/../../')
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
    did.cli.main(f"{INTERVAL} --brief")
    did.cli.main(f"{INTERVAL} --verbose")


def test_git_format():
    """ Wiki format """
    did.base.Config(CONFIG.format(GIT_PATH))
    did.cli.main(f"{INTERVAL} --format text")
    did.cli.main(f"{INTERVAL} --format wiki")


def test_git_team():
    """ Team report """
    emails = "--email psplicha@redhat.com,cward@redhat.com"
    did.base.Config(CONFIG.format(GIT_PATH))
    did.cli.main(f"{INTERVAL} {emails}")
    did.cli.main(f"{INTERVAL} {emails} --total")
    did.cli.main(f"{INTERVAL} {emails} --merge")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Content
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_git_regular():
    """ Simple git stats """
    did.base.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    assert any(
        "8a725af - Simplify git plugin tests" in stat
        for stat in stats)


def test_git_verbose():
    """ Verbose git stats """
    did.base.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main(f"{INTERVAL} --verbose")[0][0].stats[0].stats[0].stats
    assert any("tests/plugins" in stat for stat in stats)


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
    except SystemExit as exc:
        raise RuntimeError("Expected warning only") from exc


def test_git_non_existent(caplog: LogCaptureFixture):
    """ Non-existent git repo """
    did.base.Config(CONFIG.format("i-do-not-exist"))
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Unable to access git repo" in caplog.text
