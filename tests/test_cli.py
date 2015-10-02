# coding: utf-8
""" Tests for the command line script """

from __future__ import unicode_literals, absolute_import

import os
import re
import did.cli
import did.utils
from did.base import OptionError

# Prepare path and config examples
PATH = os.path.dirname(os.path.realpath(__file__))
MINIMAL = did.base.Config.example()
EXAMPLE = "".join(open(PATH + "/../examples/config").readlines())
# Substitute example git paths for real life directories
EXAMPLE = re.sub(r"\S+/git/[a-z]+", PATH, EXAMPLE)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Minimal Config
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_help_minimal():
    """ Help message with minimal config """
    did.base.Config(config=MINIMAL)
    try:
        did.cli.main(["--help"])
    except SystemExit:
        pass


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Example Config
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_help_example():
    """ Help message with example config """
    did.base.Config(config=EXAMPLE)
    try:
        did.cli.main(["--help"])
    except SystemExit:
        pass


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Invalid Arguments
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_invalid_arguments():
    """ Complain about invalid arguments """
    did.base.Config(config=MINIMAL)
    for argument in ["a", "b", "c", "something"]:
        try:
            did.cli.main(argument)
        except (SystemExit, OptionError):
            pass
        else:
            raise RuntimeError(
                "Invalid argument {0} not handled".format(argument))
