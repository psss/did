# coding: utf-8
""" Tests for the trac plugin """

import did.base
import did.cli

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CONFIG = did.base.Config.example() + """
[trac]
type = trac
url = https://fedorahosted.org/design-team/rpc
prefix = DT
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_trac_smoke():
    """ Smoke test for all stats """
    did.base.Config(CONFIG)
    stats = did.cli.main("last week")
    assert stats


def test_trac_created():
    """ Check created tickets """
    # Test on: https://fedorahosted.org/design-team/ticket/468
    did.base.Config(CONFIG)
    stats = did.cli.main("""
        --email ipanova@example.org
        --trac-created
        --since 2016-08-08
        --until 2016-08-08""")[0][0].stats[0].stats[0].stats
    assert any([
        "DT#0468 - Re-brand of pulp logo" in str(change)
        for change in stats])


def test_trac_closed():
    """ Check closed tickets """
    # Test on: https://fedorahosted.org/design-team/ticket/437
    did.base.Config(CONFIG)
    stats = did.cli.main("""
        --email maryshak1996@example.org
        --trac-closed
        --since 2016-09-22
        --until 2016-09-22""")[0][0].stats[0].stats[3].stats
    assert any([
        "DT#0437 - Icon for openQA" in str(change) for change in stats])
