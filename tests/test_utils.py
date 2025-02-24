# coding: utf-8

import os
import sys

import pytest

import did
import did.utils
from did.utils import strtobool

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_email_re():
    ''' Confirm regex works as we would expect for extracting
        name, login and email from standard email strings'''
    # good
    x = '"Chris Ward" <cward@redhat.com>'
    groups = did.utils.EMAIL_REGEXP.search(x).groups()
    assert len(groups) == 2
    assert groups[0] == 'Chris Ward'
    assert groups[1] == 'cward@redhat.com'

    x = 'cward@redhat.com'
    groups = did.utils.EMAIL_REGEXP.search(x).groups()
    assert len(groups) == 2
    assert groups[0] is None
    assert groups[1] == 'cward@redhat.com'

    # bad
    x = 'cward'
    groups = did.utils.EMAIL_REGEXP.search(x)
    assert groups is None

    # ugly
    x = '"" <>'
    groups = did.utils.EMAIL_REGEXP.search(x)
    assert groups is None


def test_log():
    assert did.utils.log
    assert did.utils.log.name == 'did'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Utils
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_import_success():
    # pylint: disable=protected-access
    s = did.utils._import("sys", True)
    assert s is sys

    s = did.utils._import("blah", True)
    assert s is None


def test_find_base():
    top = os.path.dirname(os.path.dirname(did.__file__))
    # pylint: disable=protected-access
    # we are testing the protected method _find_base
    assert top == did.utils._find_base(__file__)
    assert top == did.utils._find_base(os.path.dirname(__file__))


def test_load_components():
    top = os.path.dirname(did.__file__)
    assert did.utils.load_components(top) > 0
    assert did.utils.load_components("did.plugins") > 0


def test_import_failure():
    with pytest.raises(ImportError):
        # pylint: disable=protected-access
        did.utils._import("blah", False)


def test_header():
    assert did.utils.header


def test_shorted():
    assert did.utils.shorted


def test_item():
    assert did.utils.item


def test_pluralize():
    pluralize = did.utils.pluralize
    assert pluralize
    assert pluralize("word") == "words"
    assert pluralize("bounty") == "bounties"
    assert pluralize("mass") == "masses"


def test_listed():
    listed = did.utils.listed
    assert listed
    assert listed(range(1)) == "0"
    assert listed(range(2)) == "0 and 1"
    assert listed(range(3), quote='"') == '"0", "1" and "2"'
    assert listed(range(4), maximum=3) == "0, 1, 2 and 1 more"
    assert listed(range(5), 'number', maximum=3) == "0, 1, 2 and 2 more numbers"
    assert listed(range(6), 'category') == "6 categories"
    assert listed(7, "leaf", "leaves") == "7 leaves"
    assert listed([], "item", maximum=0) == "0 items"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Logging
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_info():
    assert did.utils.info
    did.utils.info("something")
    did.utils.info("no-new-line", newline=False)


def test_Logging():
    assert did.utils.Logging


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Coloring
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_Coloring():
    assert did.utils.Coloring


def test_color():
    assert did.utils.color


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  strtobool
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_strtobool():
    # True
    assert strtobool("yes") == 1
    assert strtobool("y") == 1
    assert strtobool("on") == 1
    assert strtobool("true") == 1
    assert strtobool("True") == 1
    assert strtobool("TRUE") == 1
    assert strtobool("1") == 1
    assert strtobool(1) == 1

    # False
    assert strtobool("no") == 0
    assert strtobool("n") == 0
    assert strtobool("off") == 0
    assert strtobool("false") == 0
    assert strtobool("False") == 0
    assert strtobool("FALSE") == 0
    assert strtobool("0") == 0
    assert strtobool(0) == 0
