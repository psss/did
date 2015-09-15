# coding: utf-8
""" Tests for the Bugzilla plugin """

from __future__ import unicode_literals, absolute_import

import did.cli
import did.base


CONFIG = """
[bz]
type = bugzilla
prefix = BZ
url = https://bugzilla.redhat.com/xmlrpc.cgi
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Linus Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_linus():
    """ Check bugs filed by Linus :-) """
    did.base.Config(CONFIG)
    did.cli.main(
        "--email torvalds@linux-foundation.org "
        "--bz-filed --until today".split())


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Week Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_week():
    """ Check all stats for given week"""
    did.base.Config(CONFIG)
    did.cli.main("--bz --email psplicha@redhat.com".split())


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Fixed Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_fixed():
    """ Check fixed bugs on BZ#1174186"""
    did.base.Config(CONFIG)
    # The first fix was not successfull (bug later moved to ASSIGNED)
    stats = did.cli.main("""
        --bz-fixed
        --email sbradley@redhat.com
        --since 2015-03-03
        --until 2015-03-03""")[0][0].stats[0].stats[3].stats
    assert not any([bug.id == 1174186 for bug in stats])
    # The second fix was successfull
    stats = did.cli.main("""
        --bz-fixed
        --email sbradley@redhat.com
        --since 2015-04-16
        --until 2015-04-16""")[0][0].stats[0].stats[3].stats
    assert any([bug.id == 1174186 for bug in stats])
