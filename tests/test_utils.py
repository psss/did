# coding: utf-8

import os

import pytest

import did

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_email_re():
    ''' Confirm regex works as we would expect for extracting
        name, login and email from standard email strings'''
    from did.utils import EMAIL_REGEXP

    # good
    x = '"Chris Ward" <cward@redhat.com>'
    groups = EMAIL_REGEXP.search(x).groups()
    assert len(groups) == 2
    assert groups[0] == 'Chris Ward'
    assert groups[1] == 'cward@redhat.com'

    x = 'cward@redhat.com'
    groups = EMAIL_REGEXP.search(x).groups()
    assert len(groups) == 2
    assert groups[0] is None
    assert groups[1] == 'cward@redhat.com'

    # bad
    x = 'cward'
    groups = EMAIL_REGEXP.search(x)
    assert groups is None

    # ugly
    x = '"" <>'
    groups = EMAIL_REGEXP.search(x)
    assert groups is None


def test_log():
    from did.utils import log
    assert log
    log.name == 'did'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Utils
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_import_success():
    import sys

    from did.utils import _import
    s = _import("sys", True)
    assert s is sys

    s = _import("blah", True)
    assert s is None


def test_find_base():
    top = os.path.dirname(os.path.dirname(did.__file__))
    assert top == did.utils._find_base(__file__)
    assert top == did.utils._find_base(os.path.dirname(__file__))


def test_load_components():
    top = os.path.dirname(did.__file__)
    assert did.utils.load_components(top) > 0
    assert did.utils.load_components("did.plugins") > 0


def test_import_failure():
    from did.utils import _import
    with pytest.raises(ImportError):
        _import("blah", False)


def test_header():
    from did.utils import header
    assert header


def test_shorted():
    from did.utils import shorted
    assert shorted


def test_item():
    from did.utils import item
    assert item


def test_pluralize():
    from did.utils import pluralize
    assert pluralize
    assert pluralize("word") == "words"
    assert pluralize("bounty") == "bounties"
    assert pluralize("mass") == "masses"


def test_listed():
    from did.utils import listed
    assert listed
    assert listed(range(1)) == "0"
    assert listed(range(2)) == "0 and 1"
    assert listed(range(3), quote='"') == '"0", "1" and "2"'
    assert listed(range(4), max=3) == "0, 1, 2 and 1 more"
    assert listed(range(5), 'number', max=3) == "0, 1, 2 and 2 more numbers"
    assert listed(range(6), 'category') == "6 categories"
    assert listed(7, "leaf", "leaves") == "7 leaves"
    assert listed([], "item", max=0) == "0 items"


def test_ascii():
    from did.utils import ascii
    assert ascii
    assert ascii("ěščřžýáíé") == "escrzyaie"
    assert ascii(0) == "0"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Logging
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_info():
    from did.utils import info
    assert info
    info("something")
    info("no-new-line", newline=False)


def test_Logging():
    from did.utils import Logging
    assert Logging


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Coloring
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_Coloring():
    from did.utils import Coloring
    assert Coloring


def test_color():
    from did.utils import color
    assert color
