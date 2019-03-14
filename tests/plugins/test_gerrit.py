# coding: utf-8
""" Tests for the Gerrit plugin """

from __future__ import unicode_literals, absolute_import

import did.cli
import did.base


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CONFIG = """
[general]
email = Dan Callaghan <dcallagh@redhat.com>

[gerrit]
type = gerrit
url = https://gerrit.beaker-project.org/
prefix = GR
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_gerrit_smoke():
    """ Smoke test for all stats """
    did.base.Config(CONFIG)
    stats = did.cli.main("last week")
    assert stats


def test_gerrit_merged():
    """ Check merged changes """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--gerrit-merged",
        "--since", "2018-09-24",
        "--until", "2018-09-30"])[0][0].stats[0].stats[1].stats
    assert any([
        "GR#6299 - expand device.fw_version column" in unicode(change)
        for change in stats])


def test_gerrit_reviewed():
    """ Check reviewed changes """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--gerrit-reviewed",
        "--since", "2018-10-20",
        "--until", "2018-10-30"])[0][0].stats[0].stats[4].stats
    assert any([
        "GR#6313 - Make beah default harness" in unicode(change)
        for change in stats])
