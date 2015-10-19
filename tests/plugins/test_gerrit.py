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
email = Bill Peck <bpeck@redhat.com>

[gerrit]
type = gerrit
url = https://gerrit.beaker-project.org/#/
prefix = GR
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_gerrit_smoke():
    """ Smoke test for all stats """
    did.base.set_config(CONFIG)
    stats = did.cli.main("last week")
    assert stats


def test_gerrit_merged():
    """ Check merged changes """
    did.base.set_config(CONFIG)
    stats = did.cli.main([
        "--since", "2015-08-01",
        "--until", "2015-08-31",
        "--gerrit-merged"])[0][0].stats[0].stats[1].stats
    assert any([
        "GR#4347 - Fix jobs.rst" in unicode(change)
        for change in stats])


def test_gerrit_reviewed():
    """ Check reviewed changes """
    did.base.set_config(CONFIG)
    stats = did.cli.main([
        "--since", "2015-08-01",
        "--until", "2015-08-31",
        "--gerrit-reviewed"])[0][0].stats[0].stats[5].stats
    assert any([
        "GR#4380 - Fix memleak" in unicode(change)
        for change in stats])
