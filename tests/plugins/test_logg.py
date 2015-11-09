# coding: utf-8

from __future__ import unicode_literals, absolute_import

import ConfigParser
import logging
import os
import pytest
import re
from datetime import date, timedelta

# simple test that import works
import did

did.utils.log.setLevel(logging.DEBUG)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

BASE_CONFIG = '''
[general]
email = "Chris Ward" <cward@redhat.com>

[joy]
type = logg

[logg]
'''.strip()
# default repo is created in ~/.did/loggs
# OVERRIDE THE ENGINE PATH so we don't destroy the user's actual
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


INTERVAL = "--since 2015-10-20 --until 2015-10-22"

did.logg.DEFAULT_ENGINE_URI = DEFAULT_ENGINE_URI


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Unit
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_defaule_logg():
    did.base.set_config(GOOD_DEFAULT_CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    assert any(["{0} {1} [{2}]".format(ARGS_OK_MIN[2][:10],
                                       ARGS_OK_MIN[1],
                                       ARGS_OK_MIN[0]) in stat
                for stat in stats])


def test_git_logg():
    did.base.set_config(GOOD_GIT_CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    assert any(["{0}".format(ARGS_OK_MIN[1]) in stat
                for stat in stats])
