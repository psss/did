# coding: utf-8
""" Tests for the Bugzilla plugin """

from __future__ import unicode_literals, absolute_import

import did.cli
import did.base


CONFIG = """
[bz]
type = bugzilla
prefix = BZ
url = https://partner-bugzilla.redhat.com/xmlrpc.cgi
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Linus Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_linus():
    """ Check bugs filed by Linus :-) """
    did.base.Config(CONFIG)
    stats = did.cli.main("""
        --email torvalds@linux-foundation.org
        --bz-filed --until today""")[0][0].stats[0].stats[0].stats
    assert any([bug.id == 439858 for bug in stats])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Week Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_week():
    """ Check all stats for given week """
    did.base.Config(CONFIG)
    stats = did.cli.main("--email psplicha@redhat.com")
    assert stats


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


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Returned Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_returned():
    """ Check returned bugs """
    did.base.Config(CONFIG)
    # Moving bug to ASSIGNED from ON_QA (test on BZ#1174186)
    stats = did.cli.main([
        "--bz-returned",
        "--email", "David Kutálek <dkutalek@redhat.com>",
        "--since", "2015-04-15",
        "--until", "2015-04-15"])[0][0].stats[0].stats[4].stats
    assert any([bug.id == 1174186 for bug in stats])
    # Moving from NEW is not returning bug (test on BZ#1229704)
    stats = did.cli.main("""
        --bz-returned
        --email mizdebsk@redhat.com
        --since 2015-06-09
        --until 2015-06-09""")[0][0].stats[0].stats[4].stats
    assert not any([bug.id == 1229704 for bug in stats])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Closed Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_closed():
    """ Check closed bugs """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--bz-closed",
        "--email", "Petr Šplíchal <psplicha@redhat.com>",
        "--since", "2012-12-06",
        "--until", "2012-12-06"])[0][0].stats[0].stats[7].stats
    assert any([bug.id == 862231 for bug in stats])
    assert any(["[duplicate]" in unicode(bug) for bug in stats])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Subscribed Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_subscribed():
    """ Check subscribed bugs """
    did.base.Config(CONFIG)
    stats = did.cli.main([
        "--bz-subscribed",
        "--email", "Evgeni Golov <egolov@redhat.com>",
        "--since", "2016-06-06",
        "--until", "2016-06-12"])[0][0].stats[0].stats[8].stats
    assert any([bug.id == 1343546 for bug in stats])
