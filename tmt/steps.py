# coding: utf-8

""" Base Metadata Classes """

from click import echo, style

import os
import fmf
import click
import pprint
import tmt.utils

STEPS = ['discover', 'provision', 'prepare', 'execute', 'report', 'finish']


class Step(object):
    """ Common parent of all test steps """
    # Test steps need to be explicitly enabled
    enabled = False

    # Required name of the step
    name = 'unknown-step'

    def __init__(self, data={}, plan=None):
        """ Store step data """
        self.data = data
        self.plan = plan
        self._workdir = None
        try:
            self.summary = data.get('summary')
        except AttributeError:
            self.summary = None

    def __str__(self):
        """ Step name """
        return self.name

    @property
    def workdir(self):
        """ Get the workdir, create if does not exist """
        if self._workdir is None:
            self._workdir = os.path.join(
                self.plan.workdir, str(self))
            tmt.utils.create_directory(self._workdir, 'workdir', quiet=True)
        return self._workdir

    def go(self):
        """ Execute the test step """
        if not self.enabled:
            return
        echo(tmt.utils.format(str(self), 'not implemented', key_color='blue'))
        echo(tmt.utils.format('workdir', self.workdir, key_color='magenta'))

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
    name = 'discover'

    def show(self):
        """ Show discover details """
        super(Discover, self).show(
            keys=['how', 'filter', 'repository', 'tests'])


class Provision(Step):
    """ Provision an environment for testing (or use localhost) """
    name = 'provision'


class Prepare(Step):
    """ Configure environment for testing (e.g. ansible playbook) """
    name = 'prepare'


class Execute(Step):
    """ Run the tests (using the specified framework and its settings) """
    name = 'execute'

    def __init__(self, data, plan):
        """ Initialize the execute step """
        super(Execute, self).__init__(data, plan)
        if not 'how' in self.data:
            self.data['how'] = 'shell'

    def show(self):
        """ Show execute details """
        super(Execute, self).show(keys=['how', 'script', 'isolate'])


class Report(Step):
    """ Provide an overview of test results and send notifications """
    name = 'report'


class Finish(Step):
    """ Additional actions to be performed after the test execution """
    name = 'finish'
