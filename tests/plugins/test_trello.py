# coding: utf-8
# Test Board: https://trello.com/b/YcOfywBd/did-testing

""" Tests for the Trello plugin """

from __future__ import unicode_literals, absolute_import

import pytest
import did.cli
import did.base

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2018-12-19 --until 2018-12-19"

CONFIG = """
[general]
email = "Did Tester" <the.did.tester@gmail.com>
[trello]
type = trello
user = didtester
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_trello_cards_created():
    """ Created cards """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    print stats
    assert any([
        "CreatedCard" in unicode(stat) for stat in stats])


def test_trello_cards_updated():
    """ Updated cards """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[1].stats
    print stats
    assert any([
        "UpdatedCard"
        in unicode(stat) for stat in stats])


def test_trello_cards_closed():
    """ Closed cards """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[2].stats
    print stats
    assert any([
        "ClosedCard: closed"
        in unicode(stat) for stat in stats])


def test_trello_cards_commented():
    """ Commented cards """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[3].stats
    print stats
    assert any([
        "CommentedCard"
        in unicode(stat) for stat in stats])


def test_trello_cards_moved():
    """ Moved cards """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[4].stats
    print stats
    assert any([
        "[MovedCard] moved from [new] to [active]"
        in unicode(stat) for stat in stats])


def test_trello_checklists_checkitem():
    """ Completed Checkitems in checklists """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[5].stats
    print stats
    # print[unicode(stat) for stat in stats]
    assert any([
        "ChecklistCard: CheckItem"
        in unicode(stat) for stat in stats])


def test_trello_missing_username():
    """ Missing username """
    did.base.Config("[trello]\ntype = trello")
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)
