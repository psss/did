# coding: utf-8
""" Tests for the git plugin """

from __future__ import unicode_literals, absolute_import

import os
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
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_git_regular():
    """ Simple git stats """
    did.utils.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    assert any([
        "8a725af - Simplify git plugin tests" in stat
        for stat in stats])

def test_git_verbose():
    """ Verbose git stats """
    did.utils.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main(INTERVAL + " --verbose")[0][0].stats[0].stats[0].stats
    assert any(["tests/plugins" in stat for stat in stats])

def test_git_nothing():
    """ No stats found """
    did.utils.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main("--until 2015-01-01")[0][0].stats[0].stats[0].stats
    assert stats == []

def test_git_invalid():
    """ Invalid git repo """
    did.utils.Config(CONFIG.format("/tmp"))
    try:
        did.cli.main(INTERVAL)
    except SystemExit:
        pass
    else:
        raise RuntimeError("Expected failure")

def test_git_non_existent():
    """ Non-existent git repo """
    did.utils.Config(CONFIG.format("i-do-not-exist"))
    try:
        did.cli.main(INTERVAL)
    except SystemExit:
        pass
    else:
        raise RuntimeError("Expected failure")
