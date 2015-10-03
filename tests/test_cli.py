# coding: utf-8
""" Tests for the command line script """

from __future__ import unicode_literals, absolute_import

import os
import re
import pytest

import did.cli
import did.base
import did.utils


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Prepare path and config examples
PATH = os.path.dirname(os.path.realpath(__file__))
MINIMAL = did.base.Config.example()
EXAMPLE = "".join(open(PATH + "/../examples/config").readlines())
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


def test_invalid_arguments():
    """ Complain about invalid arguments """
    did.base.Config(config=MINIMAL)
    for argument in ["a", "b", "c", "something"]:
        with pytest.raises(did.base.OptionError):
            did.cli.main(argument)
