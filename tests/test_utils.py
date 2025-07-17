# coding: utf-8

import logging
import os
import sys
from argparse import Namespace

import pytest
from _pytest.logging import LogCaptureFixture

import did
import did.cli
import did.utils

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_email_re() -> None:
    ''' Confirm regex works as we would expect for extracting
        name, login and email from standard email strings'''
    # good
    x = '"Chris Ward" <cward@redhat.com>'
    match = did.utils.EMAIL_REGEXP.search(x)
    assert match is not None
    groups = match.groups()
    assert len(groups) == 2
    assert groups[0] == 'Chris Ward'
    assert groups[1] == 'cward@redhat.com'

    x = 'cward@redhat.com'
    match = did.utils.EMAIL_REGEXP.search(x)
    assert match is not None
    groups = match.groups()
    assert len(groups) == 2
    assert groups[0] is None
    assert groups[1] == 'cward@redhat.com'

    # bad
    x = 'cward'
    match = did.utils.EMAIL_REGEXP.search(x)
    assert match is None

    # ugly
    x = '"" <>'
    match = did.utils.EMAIL_REGEXP.search(x)
    assert match is None


def test_log() -> None:
    assert did.utils.log
    assert did.utils.log.name == 'did'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Utils
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_import_success() -> None:
    # pylint: disable=protected-access
    s = did.utils._import("sys", True)
    assert s is sys

    s = did.utils._import("blah", True)
    assert s is None


def test_find_base() -> None:
    top = os.path.dirname(os.path.dirname(did.__file__))
    # pylint: disable=protected-access
    # we are testing the protected method _find_base
    assert top == did.utils._find_base(__file__)
    assert top == did.utils._find_base(os.path.dirname(__file__))


def test_load_components() -> None:
    top = os.path.dirname(did.__file__)
    assert did.utils.load_components(top) > 0
    assert did.utils.load_components("did.plugins") > 0


def test_import_failure() -> None:
    with pytest.raises(ImportError):
        # pylint: disable=protected-access
        did.utils._import("blah", False)


def test_header(capsys: pytest.CaptureFixture[str]) -> None:
    did.utils.header("test", separator='-', separator_width=2)
    captured = capsys.readouterr()
    assert captured.out == "\n--\n test\n--\n"


def test_shorted() -> None:
    res = did.utils.shorted("this text is longer than 6\nthis is also longer", width=6)
    assert res == "this...\nthis..."


def test_item_no_options(capsys: pytest.CaptureFixture[str]) -> None:
    did.utils.item("this is level 0 text", level=0, options=None)
    captured = capsys.readouterr()
    assert captured.out == "* this is level 0 text\n"

    did.utils.item("this is level 1 text", level=1, options=None)
    captured = capsys.readouterr()
    assert captured.out == "    * this is level 1 text\n"


def test_item_not_brief(capsys: pytest.CaptureFixture[str]) -> None:
    options = Namespace(brief=False, format="text", width=100)
    did.utils.item("this is level 0 text", level=0, options=options)
    captured = capsys.readouterr()
    assert captured.out == "\n* this is level 0 text\n"

    did.utils.item("this is level 1 text", level=1, options=options)
    captured = capsys.readouterr()
    assert captured.out == "    * this is level 1 text\n"


def test_item_brief_text(capsys: pytest.CaptureFixture[str]) -> None:
    options = Namespace(brief=True, format="text", width=100)
    did.utils.item("this is level 0 text", level=0, options=options)
    captured = capsys.readouterr()
    assert captured.out == "* this is level 0 text\n"

    did.utils.item("this is level 1 text", level=1, options=options)
    captured = capsys.readouterr()
    # brief shows only level 0
    assert captured.out == ""


def test_item_markdown(capsys: pytest.CaptureFixture[str]) -> None:
    options = Namespace(brief=False, format="markdown", width=100)

    did.utils.item("this is level 0 text", level=0, options=options)
    captured = capsys.readouterr()
    assert captured.out == "\n* this is level 0 text\n"

    did.utils.item("this is level 1 text", level=1, options=options)
    captured = capsys.readouterr()
    assert captured.out == "  * this is level 1 text\n"


def test_item_wiki(capsys: pytest.CaptureFixture[str]) -> None:
    options = Namespace(brief=False, format="wiki", width=100)

    did.utils.item("this is level 0 text", level=0, options=options)
    captured = capsys.readouterr()
    assert captured.out == "\n * this is level 0 text\n"

    did.utils.item("this is level 1 text", level=1, options=options)
    captured = capsys.readouterr()
    assert captured.out == "    * this is level 1 text\n"


def test_pluralize() -> None:
    pluralize = did.utils.pluralize
    assert pluralize("word") == "words"
    assert pluralize("bounty") == "bounties"
    assert pluralize("mass") == "masses"


def test_listed() -> None:
    listed = did.utils.listed
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

def test_info(capsys: pytest.CaptureFixture[str]) -> None:
    did.utils.info("something")
    captured = capsys.readouterr()
    assert captured.err == "something\n"
    did.utils.info("no-new-line", newline=False)
    captured = capsys.readouterr()
    assert captured.err == "no-new-line"


def test_logging(capsys: pytest.CaptureFixture[str], caplog: LogCaptureFixture) -> None:
    mylogging = did.utils.Logging('test')
    log = mylogging.logger
    mylogging.set(did.utils.LOG_INFO)
    assert mylogging.get() == did.utils.LOG_INFO
    log.info("This is printed")
    captured = capsys.readouterr()
    assert captured.err == "[INFO] This is printed\n"

    with caplog.at_level(logging.DEBUG, "test"):
        assert mylogging.get() == did.utils.LOG_DEBUG
        log.debug("debug")
        assert "debug" in caplog.text


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Coloring
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_coloring() -> None:
    mycoloring = did.utils.Coloring()
    assert not mycoloring.enabled()
    assert mycoloring.get() is did.utils.ColorMode.COLOR_AUTO
    mycoloring.set(did.utils.ColorMode.COLOR_ON)
    assert mycoloring.get() is did.utils.ColorMode.COLOR_ON
    # a call to set without arguments must not change the mode
    # if already set
    mycoloring.set()
    assert mycoloring.get() is did.utils.ColorMode.COLOR_ON
    # fails with invalid values
    with pytest.raises(ValueError, match="4 is not a valid ColorMode"):
        mycoloring.set(did.utils.ColorMode(4))


def test_color_function_exists() -> None:
    # No color sets
    res = did.utils.color(
        "text", text_color=None, background=None, light=False, enabled=True)
    assert res == "\033[0mtext\033[1;m"
    # Disabled
    res = did.utils.color(
        "text", text_color=None, background=None, light=False, enabled=False)
    assert res == "text"
    # Unknown color
    with pytest.raises(KeyError):
        # ignore typing for the purpose of
        # testing invalid values
        did.utils.color(
            "text",
            text_color="rainbow",  # type: ignore
            background=None,
            light=False,
            enabled=True)
    # Known color
    res = did.utils.color(
        "text", text_color="red", background=None, light=False, enabled=True)
    assert res == "\033[0;31mtext\033[1;m"
    # Light version
    res = did.utils.color(
        "text", text_color="red", background=None, light=True, enabled=True)
    assert res == "\033[1;31mtext\033[1;m"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  strtobool
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_strtobool() -> None:
    # True
    assert did.utils.strtobool("yes") == 1
    assert did.utils.strtobool("y") == 1
    assert did.utils.strtobool("on") == 1
    assert did.utils.strtobool("true") == 1
    assert did.utils.strtobool("True") == 1
    assert did.utils.strtobool("TRUE") == 1
    assert did.utils.strtobool("1") == 1

    # False
    assert did.utils.strtobool("no") == 0
    assert did.utils.strtobool("n") == 0
    assert did.utils.strtobool("off") == 0
    assert did.utils.strtobool("false") == 0
    assert did.utils.strtobool("False") == 0
    assert did.utils.strtobool("FALSE") == 0
    assert did.utils.strtobool("0") == 0
