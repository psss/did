# coding: utf-8

""" Step Classes """

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
        # Store data, convert to list if single config defined
        self.data = data
        if self.data is not None and not isinstance(self.data, list):
            self.data = [self.data]
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
        if self.plan.run.verbose:
            echo(tmt.utils.format(
                'workdir', self.workdir, key_color='magenta'))

    def show(self, keys=[]):
        """ Show step details """
        if not self.data:
            return
        configs = self.data if isinstance(self.data, list) else [self.data]
        for config in configs:
            echo(tmt.utils.format(
                str(self), self.summary or '', key_color='blue'))
            for key in keys or config:
                if key == 'summary':
                    continue
                try:
                    echo(tmt.utils.format(key, config[key]))
                except KeyError:
                    pass
