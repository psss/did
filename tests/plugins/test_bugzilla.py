# coding: utf-8
""" Tests for the Bugzilla plugin """

from __future__ import unicode_literals, absolute_import

import did.did
import did.utils


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
    did.utils.Config(CONFIG)
    did.did.main(
        "--email torvalds@linux-foundation.org "
        "--bz-filed --until today".split())


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Week Bugs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_bugzilla_week():
    """ Check all stats for given week"""
    did.utils.Config(CONFIG)
    did.did.main("--bz --email psplicha@redhat.com".split())
