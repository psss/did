# coding: utf-8
""" Tests for the Redmine plugin """

from __future__ import unicode_literals, absolute_import

import pytest
import did.cli
import did.base
import time


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2017-06-12 --until 2017-06-19"

CONFIG = """
[general]
email = "Petr Splichal" <psplicha@redhat.com>

[redmine]
type = redmine
url = http://projects.theforeman.org
login = 6558
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_redmine_activity():
    """ Redmine activity """
    did.base.Config(CONFIG)
    option = "--redmine-activity "
    stats = did.cli.main(option + INTERVAL)[0][0].stats[0].stats[0].stats
    assert any(
        ["puppetserver fails to restart after installation"
        in unicode(stat) for stat in stats])
