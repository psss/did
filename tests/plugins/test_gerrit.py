# coding: utf-8
""" Tests for the Gerrit plugin """

import did.base
import did.cli

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CONFIG = """
[general]
email = bcmills@google.com

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
        "--since", "2022-10-20",
        "--until", "2022-10-30"])[0][0].stats[0].stats[1].stats
    assert any([
        "GR#401835 - go - os/exec: add the Cancel and WaitDelay fields" in str(change)
        for change in stats])


def test_gerrit_reviewed():
    """ Check reviewed changes """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--gerrit-reviewed",
        "--since", "2022-10-20",
        "--until", "2022-10-30"])[0][0].stats[0].stats[4].stats
    assert any([
        "GR#446275 - go - testing: change Error to Errorf in comment" in str(change)
        for change in stats])


def test_gerrit_submitted_for_review():
    """ Check changes submitted for review """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--gerrit-submitted",
        "--since", "2022-10-20",
        "--until", "2022-10-30"])[0][0].stats[0].stats[2].stats
    assert any([
        "GR#445115 - text - cases: fix build, memory leaks, and error" in str(change)
        for change in stats])


def test_gerrit_wip():
    """ Check wip changes """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--gerrit-wip",
        "--since", "2022-07-01",
        "--until", "2022-07-30"])[0][0].stats[0].stats[3].stats
    assert any([
        "GR#416555 - sync - errgroup: propagate panics and goexits" in str(change)
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
