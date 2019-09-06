# coding: utf-8

""" Base Metadata Classes """

from __future__ import unicode_literals, absolute_import

import fmf
import click
import pprint

STEPS = ['discover', 'provision', 'prepare', 'execute', 'report', 'finish']


class Step(object):
    """ Common parent of all test steps """
    # Test steps need to be explicitly enabled
    enabled = False

    def __init__(self, data):
        """ Store step data """
        self.data = data

    def go(self):
        """ Execute the test step """
        if not self.enabled:
            return
        print(click.style('{0}:'.format(self.__class__.__name__), fg='blue'))
        pprint.pprint(self.data)


class Discover(Step):
    """ Gather information about test cases to be run """


class Provision(Step):
    """ Information about environment needed for testing """


class Prepare(Step):
    """ Additional configuration of the test environment """


class Execute(Step):
    """ Execution of individual test cases """


class Report(Step):
    """ Notifications about the test progress and results """


class Finish(Step):
    """ Actions performed after test execution is completed """
