# coding: utf-8
""" Tests for the trac plugin """

from __future__ import unicode_literals, absolute_import

import did.cli
import did.base


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CONFIG = did.base.Config.example() + """
[trac]
type = trac
url = https://fedorahosted.org/fedora-infrastructure/rpc
prefix = FI
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_trac_smoke():
    """ Smoke test for all stats """
    did.base.set_config(CONFIG)
    stats = did.cli.main("last week")
    assert stats


def test_trac_created():
    """ Check created tickets """
    # Test on: https://fedorahosted.org/fedora-infrastructure/ticket/4891
    did.base.set_config(CONFIG)
    stats = did.cli.main("""
        --email stefw@example.org
        --since 2015-09-17
        --until 2015-09-17
        --trac-created""")[0][0].stats[0].stats[0].stats

    assert any([
        "FI#4891 - Hosting docs" in unicode(change) for change in stats])


def test_trac_closed():
    """ Check closed tickets """
    # Test on: https://fedorahosted.org/fedora-infrastructure/ticket/4864
    did.base.set_config(CONFIG)
    stats = did.cli.main("""
        --email smooge@example.org
        --since 2015-08-30
        --until 2015-08-30
        --trac-closed""")[0][0].stats[0].stats[3].stats

    assert any([
        "FI#4864 - remove mdomsch" in unicode(change) for change in stats])
