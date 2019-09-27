# coding: utf-8

""" Base Metadata Classes """

from __future__ import unicode_literals, absolute_import

from click import echo, style

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
        echo(style('{0}:'.format(self.__class__.__name__), fg='blue'))
        pprint.pprint(self.data)


class Discover(Step):
    """ Gather and show information about test cases to be executed """


class Provision(Step):
    """ Provision an environment for testing (or use localhost) """


class Prepare(Step):
    """ Configure environment for testing (e.g. ansible playbook) """


class Execute(Step):
    """ Run the tests (using the specified framework and its settings) """


class Report(Step):
    """ Provide an overview of test results and send notifications """


class Finish(Step):
    """ Additional actions to be performed after the test execution """
