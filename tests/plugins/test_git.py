# coding: utf-8
""" Tests for the git plugin """

from __future__ import unicode_literals, absolute_import

import os
import did.did
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
    did.did.main(INTERVAL)

def test_git_verbose():
    """ Verbose git stats """
    did.utils.Config(CONFIG.format(GIT_PATH))
    did.did.main(INTERVAL + " --verbose")

def test_git_invalid():
    """ Invalid git repo """
    did.utils.Config(CONFIG.format("i-do-not-exist"))
    try:
        did.did.main(INTERVAL)
    except SystemExit:
        pass
    else:
        raise RuntimeError("Expected failure")
