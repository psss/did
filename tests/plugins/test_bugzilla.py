# coding: utf-8
""" Tests for the Bugzilla plugin """

from __future__ import unicode_literals, absolute_import

import did.cli
import did.base


CONFIG = """
[general]
email = "Chris Ward" <cward@redhat.com>

[bz]
type = bugzilla
prefix = BZ
url = https://partner-bugzilla.redhat.com/xmlrpc.cgi
""".strip()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Linus Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_linus():
    """ Check bugs filed by Linus :-) """
    did.base.set_config(CONFIG)
    cmd = """
        --email torvalds@linux-foundation.org
        --since 2008-03-01
        --until 2008-04-01
        --bz-filed"""
    stats = did.cli.main(cmd)[0][0].stats[0].stats[0].stats
    assert any([bug.id == 439858 for bug in stats])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Week Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_week():
    """ Check all stats for given week """
    did.base.set_config(CONFIG)
    stats = did.cli.main("--email psplicha@redhat.com")
    assert stats


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Fixed Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_fixed():
    """ Check fixed bugs on BZ#1174186"""
    # Pass CONFIG to main directly; let's not rely on module level changes;
    # we can't predict how they affect future tests that run and expect
    # default module conditions
    # The first fix was not successfull (bug later moved to ASSIGNED)
    stats = did.cli.main("""
        --email sbradley@redhat.com
        --since 2015-03-03
        --until 2015-03-03
        --bz-fixed""", CONFIG)[0][0].stats[0].stats[3].stats
    assert not any([bug.id == 1174186 for bug in stats])
    # The second fix was successfull
    stats = did.cli.main("""
        --email sbradley@redhat.com
        --since 2015-04-16
        --until 2015-04-16
        --bz-fixed""", CONFIG)[0][0].stats[0].stats[3].stats
    assert any([bug.id == 1174186 for bug in stats])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Returned Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_returned():
    """ Check returned bugs """
    # Moving bug to ASSIGNED from ON_QA (test on BZ#1174186)
    stats = did.cli.main([
        "--email", "David Kutálek <dkutalek@redhat.com>",
        "--since", "2015-04-15",
        "--until", "2015-04-15",
        "--bz-returned"], CONFIG)[0][0].stats[0].stats[4].stats
    assert any([bug.id == 1174186 for bug in stats])
    # Moving from NEW is not returning bug (test on BZ#1229704)
    stats = did.cli.main("""
        --email mizdebsk@redhat.com
        --since 2015-06-09
        --until 2015-06-09
        --bz-returned""", CONFIG)[0][0].stats[0].stats[4].stats
    assert not any([bug.id == 1229704 for bug in stats])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Closed Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_closed():
    """ Check closed bugs """
    stats = did.cli.main([
        "--email", "Petr Šplíchal <psplicha@redhat.com>",
        "--since", "2012-12-06",
        "--until", "2012-12-06",
        "--bz-closed"], CONFIG)[0][0].stats[0].stats[7].stats
    assert any([bug.id == 862231 for bug in stats])
    assert any(["[duplicate]" in unicode(bug) for bug in stats])
