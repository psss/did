# -*- coding: utf-8 -*-
# @Author: Eduard Trott
# Test Board: https://trello.com/b/sH1cMiyg/public-test-board

""" Tests for the Trello plugin """

from __future__ import unicode_literals, absolute_import

import pytest
import did.cli
import did.base

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2015-10-01 --until 2015-10-03"

CONFIG = """
[general]
email = "Eduard Trott" <etrott@redhat.com>
[trello]
type = trello
user = maybelinot
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_trello_cards_created():
    """ Created cards """
    did.base.set_config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    print stats
    assert any([
        "Card2" in unicode(stat) for stat in stats])


def test_trello_cards_updated():
    """ Updated cards """
    did.base.set_config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[1].stats
    print stats
    assert any([
        "Card4"
        in unicode(stat) for stat in stats])


def test_trello_cards_closed():
    """ Closed cards """
    did.base.set_config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[2].stats
    print stats
    assert any([
        "Archived Card: closed"
        in unicode(stat) for stat in stats])


def test_trello_cards_moved():
    """ Moved cards """
    did.base.set_config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[3].stats
    print stats
    assert any([
        "[Card3] moved from [List1] to [List3]"
        in unicode(stat) for stat in stats])


def test_trello_checklists_checkitem():
    """ Completed Checkitems in checklists """
    did.base.set_config(CONFIG)
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[4].stats
    print stats
    # print[unicode(stat) for stat in stats]
    assert any([
        "Card1: CheckItem3"
        in unicode(stat) for stat in stats])


def test_trello_missing_apikey():
    """ Missing username """
    did.base.set_config("[trello]\ntype = trello")
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)
