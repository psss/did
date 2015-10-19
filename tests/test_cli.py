# coding: utf-8
# @ Author: "Chris Ward" <cward@redhat.com>

""" Tests for the command line script """

from __future__ import unicode_literals, absolute_import

import os
import re
import sys
import tempfile
import pytest

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Prepare path and config examples
PATH = os.path.dirname(os.path.realpath(__file__))
# copy/paste from did.base.Config.example()
MINIMAL = "[general]\nemail = Name Surname <email@example.org>\n"
EXAMPLE = "".join(open(PATH + "/../examples/config").readlines())
# Substitute example git paths for real life directories
EXAMPLE = re.sub(r"\S+/git/[a-z]+", PATH, EXAMPLE)
GIT_ENGINE_PATH = '/tmp/logg.git'

# Logg configs
BASE_CONFIG = '''
[general]
email = "Chris Ward" <cward@redhat.com>
'''.strip()

LOG_CONFIG = BASE_CONFIG + '\n\n' + '''
[logg]
type = logg
'''.strip()

# default repo is created in ~/.did/loggs
# OVERRIDE THE ENGINE PATE so we don't destroy the user's actual
# db on accident
DEFAULT_ENGINE_PATH = '/tmp/logg.txt'
GIT_ENGINE_PATH = '/tmp/logg.git'

_DEFAULT_ENGINE = '\n{0}\nengine = txt://{1}\njoy = Joy of the Week'
GOOD_LOG_CONFIG = _DEFAULT_ENGINE.format(LOG_CONFIG, DEFAULT_ENGINE_PATH)

_GIT_ENGINE = '{0}\nengine = git://{1}\njoy = Joy of the Week'
GOOD_GIT_CONFIG = _GIT_ENGINE.format(LOG_CONFIG, GIT_ENGINE_PATH)
STRICT_GIT_CONFIG = GOOD_GIT_CONFIG + '\nstrict = true'
NOT_STRICT_GIT_CONFIG = GOOD_GIT_CONFIG + '\nstrict = false'

_logg = "did logg joy test 1 2 3"
_date = "2015-10-21T07:28:00 +0000"
ARGS_OK_MIN = [_date, "joy", _logg]
ARGS_TOPIC_NO_CONFIG = [_date, "not_in_config", _logg]
ARGS_NO_DATE = ["joy", _logg]
ARGS_NO_DATE_NO_TOPIC = [_logg]

RESULT_OK_MIN = "2015-10-21 did logg joy test 1 2 3 [joy]"
# NOTE git version 1.8 doesn't include the Date: ... line
# git 2.4 does
# FIXME: conditionally check the line according to git version
#RESULT_OK_GIT = re.compile(r'\[joy \w+\] did logg joy test 1 2 3\n '
#                           'Date: Wed Oct 21 07:28:00 2015 \+0000')
RESULT_OK_GIT = re.compile(r'\[joy \w+\] did logg joy test 1 2 3')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  did Test Environment Set-up
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# OVERRIDE DEFAULT DID CONFIG TO AVOID USING USER'S PERSONAL CONFIG FILE
tmpd = tempfile.mkdtemp()
os.environ['DID_DIR'] = tmpd

TMP_CONFIG = os.path.join(tmpd, 'config')

import did.cli

import did.base
did.base.set_config(path=TMP_CONFIG)

import did.logg
# avoid using the default engine dir in case user has something there...
did.logg.DEFAULT_ENGINE_DIR = tmpd

# We are running pytest, so there will be args present
# sys.argv which need to be removed to simulate an actual
# exec of did from the cli since the parser falls back to check
# args in sys.argv because of the use of argparser's argparse
# command in did.cli
# ...
# opt, arg = self.parser.parse_known_args(arguments)
# ...
cmd = sys.argv[0]
assert 'py' in cmd and 'test' in cmd

fake_argv = ['/bin/did']
sys.argv = fake_argv


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Utils
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def check_gitlogg_commit_k(x, config=GOOD_GIT_CONFIG):
    # check the expected number of commits have been made
    l = did.logg.GitLogg(config=config)
    commits = list(l.logg_repo.iter_commits())
    assert len(commits) == x


def clean_git():
    did.utils.remove_path(GIT_ENGINE_PATH)
    assert not os.path.exists(GIT_ENGINE_PATH)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# NOTE: and calls to main() will auto set did.base.DID_CONFIG!

def test_default_no_args_cli():
    did.utils.remove_path(GIT_ENGINE_PATH)

    # when config is None did defaults to using did.base.CONFIG
    # default config path and depending on if this config file exists or not
    # did might print out a default report
    # Since this is a test, we want to avoid using the default did config
    # though just in case the testing user is running in his 'production' env

    # We changed the did.base.CONFIG to a random temporary directory in the
    # header. See line 66 or so...

    # loading from a file that doesn't exist should cause did to except
    with pytest.raises(did.base.ConfigFileError):
        did.cli.main()

    # touch the config file, now when we run it again,
    with open(TMP_CONFIG, 'w') as f:
        f.write('')
    did.base.set_config(path=TMP_CONFIG)
    # it will still crash because of an invalid conf (missing general section)
    with pytest.raises(did.base.ConfigFileError):
        did.cli.main()

    # include the minimum config [general] section with email = ...
    # which should now make main() pass
    with open(TMP_CONFIG, 'w') as f:
        f.write(BASE_CONFIG)
    did.base.set_config(path=TMP_CONFIG)
    did.cli.main()

    did.utils.remove_path(TMP_CONFIG)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Logg
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_default_logg():
    clean_git()
    r = did.cli.main(ARGS_OK_MIN, GOOD_LOG_CONFIG, is_logg=True)
    assert os.path.exists(DEFAULT_ENGINE_PATH)
    assert r == RESULT_OK_MIN


def test_default_git_logg():
    clean_git()
    r = did.cli.main(ARGS_OK_MIN, GOOD_GIT_CONFIG, is_logg=True)
    assert os.path.exists(GIT_ENGINE_PATH)
    assert RESULT_OK_GIT.search(r)
    check_gitlogg_commit_k(2)


def test_topic_not_configed():
    clean_git()
    # running this should be OK by default (strict == False)
    did.cli.main(ARGS_TOPIC_NO_CONFIG, GOOD_GIT_CONFIG, is_logg=True)
    did.cli.main(ARGS_TOPIC_NO_CONFIG, NOT_STRICT_GIT_CONFIG, is_logg=True)
    # but with strict == True, we have an exception
    with pytest.raises(did.base.ConfigError):
        did.cli.main(ARGS_TOPIC_NO_CONFIG, STRICT_GIT_CONFIG, is_logg=True)
    check_gitlogg_commit_k(3)


def test_logg_api():
    clean_git()
    # running this should be OK by default (strict == False)
    r = did.cli.main(ARGS_NO_DATE, GOOD_GIT_CONFIG, is_logg=True)
    # %d comes back as 01 but git doesn't zero-pad the days
    # so on a day like first of november %d is 01 but git shows just 1
    assert re.match('\[joy \w+\]', r)

    # git version 1.8 doesn't include the Date: ... string in the summary
    # git version 2.4 does; FIXME: need to conditionally check this depending
    # on git version installed ...
    #now = did.base.Date().date.strftime("%a %b")
    #assert re.search(now, r)

    # strict = False by default, so this shouldn't fail
    r = did.cli.main(ARGS_NO_DATE_NO_TOPIC, GOOD_GIT_CONFIG, is_logg=True)

    # test that the target topic is 'unsorted'
    assert re.match('\[unsorted \w+\]', r)

    # this fails since
    # 'unsorted' isn't defined in config
    check_gitlogg_commit_k(3)


# with pytest.raises(did.base.OptionError):

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Report
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_help_minimal():
    """ Help message with minimal config """
    with pytest.raises(SystemExit):
        did.cli.main(["--help"], MINIMAL)


def test_help_example():
    """ Help message with example config """
    did.base.Config(config=EXAMPLE)
    with pytest.raises(SystemExit):
        did.cli.main(["--help"])


def test_invalid_arguments():
    """ Complain about invalid arguments """
    for argument in ["a", "b", "c", "something"]:
        with pytest.raises(did.base.OptionError):
            did.cli.main(argument, MINIMAL)


def test_invalid_date():
    """ Complain about invalid arguments """
    for argument in ["--since x", "--since 2015-16-17"]:
        with pytest.raises(did.base.OptionError):
            did.cli.main(argument, MINIMAL)
