# coding: utf-8

""" Base Metadata Classes """

from click import echo, style

import fmf
import click
import pprint
import tmt.utils

STEPS = ['discover', 'provision', 'prepare', 'execute', 'report', 'finish']


class Step(object):
    """ Common parent of all test steps """
    # Test steps need to be explicitly enabled
    enabled = False

    def __init__(self, data={}):
        """ Store step data """
        self.data = data
        try:
            self.summary = data.get('summary')
        except AttributeError:
            self.summary = None

    def __str__(self):
        """ Step name """
        return self.__class__.__name__.lower()

    def go(self):
        """ Execute the test step """
        if not self.enabled:
            return
        echo(tmt.utils.format(str(self), 'not implemented', key_color='blue'))

    def show(self, keys=[]):
        """ Show step details """
        if not self.data:
            return
        echo(tmt.utils.format(str(self), self.summary or '', key_color='blue'))
        for key in keys or self.data:
            if key == 'summary':
                continue
            try:
                echo(tmt.utils.format(key, self.data[key]))
            except KeyError:
                pass

class Discover(Step):
    """ Gather and show information about test cases to be executed """

    def show(self):
        """ Show discover details """
        super(Discover, self).show(
            keys=['how', 'filter', 'repository', 'tests'])

class Provision(Step):
    """ Provision an environment for testing (or use localhost) """


class Prepare(Step):
    """ Configure environment for testing (e.g. ansible playbook) """


class Execute(Step):
    """ Run the tests (using the specified framework and its settings) """

    def __init__(self, data):
        """ Initialize the execute step """
        super(Execute, self).__init__(data)
        if not 'how' in self.data:
            self.data['how'] = 'shell'

    def show(self):
        """ Show execute details """
        super(Execute, self).show(keys=['how', 'script', 'isolate'])


class Report(Step):
    """ Provide an overview of test results and send notifications """


class Finish(Step):
    """ Additional actions to be performed after the test execution """
