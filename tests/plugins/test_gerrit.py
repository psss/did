# coding: utf-8
""" Tests for the Gerrit plugin """

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
        "GR#6299 - beaker - expand device.fw_version column" in str(change)
        for change in stats])


def test_gerrit_reviewed():
    """ Check reviewed changes """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--gerrit-reviewed",
        "--since", "2018-10-20",
        "--until", "2018-10-30"])[0][0].stats[0].stats[4].stats
    assert any([
        "GR#6313 - beaker - Make beah default harness" in str(change)
        for change in stats])


def test_gerrit_wip():
    """ Check wip changes """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--gerrit-wip",
        "--since", "2015-05-01",
        "--until", "2016-10-31"])[0][0].stats[0].stats[3].stats
    assert any([
        "GR#4211 - beaker - WIP JSONAPI for system pools" in str(change)
        for change in stats])


def test_gerrit_wip_disabled():
    """ Check wip changes when the wip feature is disabled """
    CONFIG_NO_WIP = CONFIG + 'wip = False\n'
    did.base.Config(CONFIG_NO_WIP)
    stats = did.cli.main([
        "--gerrit-wip",
        "--since", "2015-05-01",
        "--until", "2016-10-31"])[0][0].stats[0].stats[3].stats
    assert stats == []
