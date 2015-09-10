# coding: utf-8
""" Tests for the command line script """

from __future__ import unicode_literals, absolute_import

import os
import re
import did.cli
import did.utils

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
