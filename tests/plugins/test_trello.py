# coding: utf-8
# Test Board: https://trello.com/b/YcOfywBd/did-testing

""" Tests for the Trello plugin """

import pytest

import did.base
import did.cli

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

def test_trello_cards_commented():
    """ Commented cards """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    assert any([
        "CommentedCard"
        in str(stat) for stat in stats])


def test_trello_cards_created():
    """ Created cards """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[1].stats
    assert any([
        "CreatedCard" in str(stat) for stat in stats])


def test_trello_cards_updated():
    """ Updated cards """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[2].stats
    assert any([
        "UpdatedCard"
        in str(stat) for stat in stats])


def test_trello_cards_closed():
    """ Closed cards """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[3].stats
    assert any([
        "ClosedCard: closed"
        in str(stat) for stat in stats])


def test_trello_cards_moved():
    """ Moved cards """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[4].stats
    assert any([
        "[MovedCard] moved from [new] to [active]"
        in str(stat) for stat in stats])


def test_trello_checklists_checkitem():
    """ Completed Checkitems in checklists """
    did.base.Config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[5].stats
    assert any([
        "ChecklistCard: CheckItem"
        in str(stat) for stat in stats])


def test_trello_missing_username():
    """ Missing username """
    did.base.Config("[trello]\ntype = trello")
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)
