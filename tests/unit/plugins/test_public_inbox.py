# coding: utf-8
""" Tests for the Public Inbox plugin """

import did.base
import did.cli

CONFIG = """
[lore]
type = public-inbox
url = https://lore.kernel.org
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Week mails
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_lore_week():
    """ Check all stats for given week """
    did.base.Config(CONFIG)
    stats = did.cli.main("--email mripard@kernel.org")
    assert stats


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  No mails posted
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_lore_none():
    """ Check new mail threads started by the user """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--email", "mripard@kernel.org",
        "--since", "2023-12-25",
        "--until", "2023-12-31"])[0][0].stats[0].stats[0].stats

    assert len(stats) == 0


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  New mails started
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_lore_started():
    """ Check new mail threads started by the user """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--lore-started",
        "--email", "mripard@kernel.org",
        "--since", "2023-12-04",
        "--until", "2023-12-10"])[0][0].stats[0].stats[0].stats

    assert len(stats) == 3
    assert any(
        msg.id() == "20231204121707.3647961-1-mripard@kernel.org"
        for msg in stats)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Mails threads the user was involved in
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_lore_involved():
    """ Check new mail threads the user was involved in """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--lore-involved",
        "--email", "mripard@kernel.org",
        "--since", "2023-12-04",
        "--until", "2023-12-10"])[0][0].stats[0].stats[1].stats

    assert len(stats) == 35
    assert any(
        msg.id() == "20231204073231.1164163-1-arnd@kernel.org"
        for msg in stats)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Mails threads the user replied to themselves
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_lore_reply_to_themselves():
    """ Check new mail threads started by and replied to the user"""
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--email", "mripard@redhat.com",
        "--since", "2024-02-26",
        "--until", "2024-03-03"])

    assert stats

    started = stats[0][0].stats[0].stats[0].stats
    assert len(started) == 3

    involved = stats[0][0].stats[0].stats[1].stats
    assert len(involved) == 0
