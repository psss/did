# coding: utf-8

from __future__ import unicode_literals, absolute_import

import logging
import os
import pytest
import shutil

# import did.base

# simple test that import works
from did.base import ConfigError
from did.logg import Logg
import did.utils

did.utils.log.setLevel(logging.DEBUG)

BASE_CONFIG = '''
[general]
email = "Chris Ward" <cward@redhat.com>

[logg]
type = logg
engine = git:///tmp/test.git
'''.strip()
# default repo is created in ~/.did/loggs
# OVERRIDE THE ENGINE PATE so we don't destroy the user's actual
# db on accident
ENGINE_PATH = '/tmp/test.git'

GOOD_CONFIG = CONFIG = BASE_CONFIG + '\njoy = Joy of the Week'

ARGS_OK_MIN = ["logg", "joy", "'did logg joy test 1 2 3'"]


# CAREFUL NOT TO DO ANYTHING IN THE USER'S ACTUAL HOME DIRECTORY!
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Sanity
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bad_args():
    from did.logg import Logg

    # Sanity: test good args which shouldn't cause any exception...
    Logg(['logg', 'joy', 'The most amazing thing happened today...'],
         config=GOOD_CONFIG)

    # Empty args doesn't fly
    with pytest.raises(ValueError):
        Logg(None)
    with pytest.raises(ValueError):
        Logg([])

    # These fail because no args or config specified
    with pytest.raises(ValueError):
        Logg([], config='')
    # with Bad Config...
    with pytest.raises(ConfigError):
        Logg(['logg', 'joy', 'The most amazing thing happened today...'],
             config='')
    # 'joy' target isn't defined in the config
    with pytest.raises(ConfigError):
        Logg(['logg', 'joy', 'The most amazing thing happened today...'],
             config='[logg] \nwork = did it, yes I did!')

    # config is ok, but args isn't
    with pytest.raises(ValueError):
        Logg(None, config='[logg]')
    with pytest.raises(ValueError):
        Logg([], config='[logg]')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Unity
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_default_logg():
    # remove the git repo if it happens to exist;
    if os.path.exists(ENGINE_PATH):
        shutil.rmtree(ENGINE_PATH)

    # load a log instance, which should create the repo if it doesn't exist
    l = Logg(ARGS_OK_MIN, config=GOOD_CONFIG)

    assert os.path.exists(ENGINE_PATH)

    assert l.target == ARGS_OK_MIN[1]
    assert l.record == ARGS_OK_MIN[2]

    l.logg_record()

    commits = list(l.logg_repo.iter_commits())
    assert len(commits) == 2

# test

# ... that default branch is created 'master' if no other branches/targets
# configured in config file

# ... that only branches defined in config or master can be used

#
