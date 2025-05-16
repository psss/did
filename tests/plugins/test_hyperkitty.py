# coding: utf-8
""" Tests for the Public Inbox plugin """

import logging

from _pytest.logging import LogCaptureFixture

import did.base
import did.cli

CONFIG = """
[virt]
type = hyperkitty
url = https://lists.centos.org/hyperkitty/list/virt@lists.centos.org/
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Week mails
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_week():
    """ Check all stats for given week """
    did.base.Config(CONFIG)
    stats = did.cli.main("--email sbonazzo@redhat.com")
    assert stats


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  No mails posted
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_none():
    """ Check new mail threads started by the user """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--email", "sbonazzo@redhat.com",
        "--since", "2024-12-25",
        "--until", "2024-12-31"])[0][0].stats[0].stats[0].stats

    assert len(stats) == 0


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  New mails started
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_started():
    """ Check new mail threads started by the user """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--virt-started",
        "--email", "sbonazzo@redhat.com",
        "--since", "2025-02-01",
        "--until", "2025-02-15"])[0][0].stats[0].stats[0].stats

    assert len(stats) == 2
    assert any([
        msg.id() == "173943744689.530355.3614994439616108884@mmx1.rdu2.centos.org"
        for msg in stats])


def test_markdown(capsys):
    """ Check markdown output """
    did.base.Config(CONFIG)
    did.cli.main([
        "--virt-started",
        "--format=markdown",
        "--email", "sbonazzo@redhat.com",
        "--since", "2025-02-01",
        "--until", "2025-02-15"])
    captured = capsys.readouterr()
    assert any([
        "[[CentOS-virt] Proposing to drop CentOS Virt SIG meeting](https://lis" in c
        for c in captured])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Mails threads the user was involved in
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_virt_involved():
    """ Check new mail threads the user was involved in """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--virt-involved",
        "--email", "sbonazzo@redhat.com",
        "--since", "2018-05-10",
        "--until", "2018-05-27"])[0][0].stats[0].stats[1].stats

    assert len(stats) == 1
    assert stats[0].id() == \
        "CAORfjXRhzitjwGPw-7jG0nsNp13sa3mLQjQvGwTJy473ipMrPA@mail.gmail.com"


def test_missing_url(caplog: LogCaptureFixture):
    did.base.Config("[virt]\ntype = hyperkitty\n")
    with caplog.at_level(logging.ERROR):
        did.cli.main([
            "--email", "sbonzzo@redhat.com",
            "--since", "2018-05-20",
            "--until", "2018-05-27"])
        assert "Skipping section virt due to error: No url in" in caplog.text
