# coding: utf-8
""" Tests for the Gerrit plugin """

import did.base
import did.cli

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CONFIG = """
[general]
email = jayconrod@google.com

[gerrit]
type = gerrit
url = https://go-review.googlesource.com/#/
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
        "--since", "2020-06-01",
        "--until", "2020-06-30"])[0][0].stats[0].stats[1].stats
    assert any([
        "GR#238157 - go - cmd: update golang.org/x/tools" in str(change)
        for change in stats])


def test_gerrit_reviewed():
    """ Check reviewed changes """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--gerrit-reviewed",
        "--since", "2020-06-01",
        "--until", "2020-06-30"])[0][0].stats[0].stats[4].stats
    assert any([
        "GR#237177 - go - cmd/go/internal/web" in str(change)
        for change in stats])


def test_gerrit_submitted_for_review():
    """ Check changes submitted for review """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--gerrit-submitted",
        "--since", "2020-06-01",
        "--until", "2020-06-30"])[0][0].stats[0].stats[2].stats
    assert any([
        "GR#240458 - go - cmd/go/internal/modfetch" in str(change)
        for change in stats])


def test_gerrit_wip():
    """ Check wip changes """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--gerrit-wip",
        "--since", "2020-06-01",
        "--until", "2020-06-30"])[0][0].stats[0].stats[3].stats
    assert any([
        "GR#237584 - go - doc: update install instructions" in str(change)
        for change in stats])


def test_gerrit_wip_disabled():
    """ Check wip changes when the wip feature is disabled """
    CONFIG_NO_WIP = CONFIG + 'wip = False\n'
    did.base.Config(CONFIG_NO_WIP)
    stats = did.cli.main([
        "--gerrit-wip",
        "--since", "2020-06-01",
        "--until", "2020-06-30"])[0][0].stats[0].stats[3].stats
    assert stats == []
