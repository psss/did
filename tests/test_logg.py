# coding: utf-8

from __future__ import unicode_literals, absolute_import

import ConfigParser
import logging
import os
import pytest
import re

# simple test that import works
import did

did.utils.log.setLevel(logging.DEBUG)

BASE_CONFIG = '''
[general]
email = "Chris Ward" <cward@redhat.com>

[logg]
type = logg
'''.strip()
# default repo is created in ~/.did/loggs
# OVERRIDE THE ENGINE PATE so we don't destroy the user's actual
# db on accident
DEFAULT_ENGINE_PATH = '/tmp/logg.txt'
GIT_ENGINE_PATH = '/tmp/logg.git'

DEFAULT_ENGINE_URI = 'txt://{0}'.format(DEFAULT_ENGINE_PATH)

_DEFAULT_ENGINE = '{0}\nengine = {1}\njoy = Joy of the Week'
GOOD_DEFAULT_CONFIG = _DEFAULT_ENGINE.format(BASE_CONFIG, DEFAULT_ENGINE_URI)

_GIT_ENGINE = '{0}\nengine = git://{1}\njoy = Joy of the Week'
GOOD_GIT_CONFIG = _GIT_ENGINE.format(BASE_CONFIG, GIT_ENGINE_PATH)
STRICT_GIT_CONFIG = GOOD_GIT_CONFIG + '\nstrict = true'

ARGS_OK_MIN = ["joy", "did logg joy test 1 2 3", '2015-10-21T07:28:00 +0000']

# NOTE git version 1.8 doesn't include the Date: ... line
# git 2.4 does
# FIXME: conditionally check the line according to git version
#RESULT_OK_GIT = re.compile(r'\[joy \w+\] did logg joy test 1 2 3\n '
#                           'Date: Wed Oct 21 07:28:00 2015 \+0000')
RESULT_OK_GIT = re.compile(r'\[joy \w+\] did logg joy test 1 2 3')


# CAREFUL NOT TO DO ANYTHING IN THE USER'S ACTUAL HOME DIRECTORY!
# monkey patch the DEFAULT_ENGINE_URI which normally points to
# ~/.did/loggs/did-$user.txt
did.logg.DEFAULT_ENGINE_URI = DEFAULT_ENGINE_URI


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Sanity
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_args():
    Logg = did.logg.Logg

    # Sanity: test good args which shouldn't cause any exception...
    Logg(config=GOOD_GIT_CONFIG).logg_record(
        target='joy', record='The most amazing thing happened today...')

    # "Empty" config is ok; defaults set are reasonable
    assert Logg()
    assert Logg(None)
    assert Logg('')
    assert Logg([])

    # config is bad
    with pytest.raises(ConfigParser.MissingSectionHeaderError):
        Logg(config='[logg')
    with pytest.raises(ConfigParser.MissingSectionHeaderError):
        Logg('[]')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Unit
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_default_logg():
    did.utils.remove_path(DEFAULT_ENGINE_PATH)
    # ## FIXTURE ## #
    # load a log instance, but it shouldn't create a
    # repo yet, it's lazy
    l = did.logg.Logg(config=GOOD_DEFAULT_CONFIG)
    assert not os.path.exists(DEFAULT_ENGINE_PATH)
    # repo will be created only if commit is called
    # which then should create the repo if it doesn't exist
    # ## FIXTURE ## #

    l.logg_record(*ARGS_OK_MIN)

    assert l._target == ARGS_OK_MIN[0]
    assert l._record == ARGS_OK_MIN[1]

    # now the repo should exist
    assert os.path.exists(DEFAULT_ENGINE_PATH)


def test_git_logg():
    did.utils.remove_path(GIT_ENGINE_PATH)

    l = did.logg.GitLogg(config=GOOD_GIT_CONFIG)
    r = l.logg_record(*ARGS_OK_MIN)

    # the sha changes
    assert RESULT_OK_GIT.match(r)

    commits = list(l.logg_repo.iter_commits())
    assert len(commits) == 2

# test

# ... that default branch is created 'master' if no other branches/targets
# configured in config file

# ... that only branches defined in config or master can be used
