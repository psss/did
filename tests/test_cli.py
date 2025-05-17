# coding: utf-8
""" Tests for the command line script """

import os
import re

import pytest

import did.base
import did.cli
import did.utils

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Prepare path and config examples
PATH = os.path.dirname(os.path.realpath(__file__))
MINIMAL = did.base.Config.example()
EXAMPLE = ""
with open(os.path.join(PATH, "..", "examples", "config"), encoding="utf-8") as example:
    EXAMPLE = "".join(example.readlines())
# Substitute example git paths for real life directories
EXAMPLE = re.sub(r"\S+/git/[a-z]+", PATH, EXAMPLE)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_help_minimal():
    """ Help message with minimal config """
    did.base.Config(config=MINIMAL)
    with pytest.raises(SystemExit):
        did.cli.main(["--help"])


def test_help_example():
    """ Help message with example config """
    did.base.Config(config=EXAMPLE)
    with pytest.raises(SystemExit):
        did.cli.main(["--help"])


def test_debug():
    """ Check the debug mode """
    did.base.Config(config=EXAMPLE)
    with pytest.raises(SystemExit):
        did.cli.main("--help --debug")


def test_invalid_arguments():
    """ Complain about invalid arguments """
    did.base.Config(config=MINIMAL)
    for argument in ["a", "b", "c", "something"]:
        with pytest.raises(did.base.OptionError):
            did.cli.main(argument)


def test_invalid_date():
    """ Complain about invalid arguments """
    did.base.Config(config=MINIMAL)
    for argument in ["--since x", "--since 2015-16-17"]:
        with pytest.raises(did.base.OptionError):
            did.cli.main(argument)
