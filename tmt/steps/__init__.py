# coding: utf-8

""" Step Classes """

import os
import fmf
import click
import pprint
import tmt.utils

from click import echo, style
from tmt.utils import GeneralError

STEPS = ['discover', 'provision', 'prepare', 'execute', 'report', 'finish']


class Step(tmt.utils.Common):
    """ Common parent of all test steps """

    # Default implementation for all steps is shell
    # except for provision (virtual) and report (display)
    how = 'shell'

    def __init__(self, data={}, plan=None, name=None):
        """ Initialize and check the step data """
        super(Step, self).__init__(name=name, parent=plan)
        # Initialize data
        self.plan = plan
        self.data = data

        # Create an empty step by default (can be updated from cli)
        if self.data is None:
            self.data = [{'name': 'one'}]
        # Convert to list if only a single config provided
        elif isinstance(self.data, dict):
            # Give it a name unless defined
            if not self.data.get('name'):
                self.data['name'] = 'one'
            self.data = [self.data]
        # Shout about invalid configuration
        elif not isinstance(self.data, list):
            raise GeneralError(f"Invalid '{self}' config in '{self.plan}'.")

        # Final sanity checks
        for data in self.data:
            # Set 'how' to the default if not specified
            if data.get('how') is None:
                data['how'] = self.how
            # Ensure that each config has a name
            if 'name' not in data and len(self.data) > 1:
                raise GeneralError(f"Missing '{self}' name in '{self.plan}'.")
        # Get or set the status
        if self.status is None:
            self.status('todo')

    @property
    def verbose(self):
        """ Verbose mode output, by default off """
        return self.plan.run and self.plan.run.opt('verbose')

    def load(self):
        """ Load step data from the workdir """
        pass

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        # Check workdir for possible stored data
        self.load()

        # Override data with command line input
        for step in self.data:
            how = self.opt('how')
            if how is not None:
                step['how'] = how

    def go(self):
        """ Execute the test step """
        # Show step header
        echo(tmt.utils.format(str(self), '', key_color='blue'))
        # Show workdir in verbose mode
        if self.verbose:
            echo(tmt.utils.format(
                'workdir', self.workdir, key_color='magenta'))

    def show(self, keys=[]):
        """ Show step details """
        for step in self.data:
            # Show empty steps only in verbose mode
            if len(step.keys()) == 1 and not self.verbose:
                continue
            # Step name (and optional header)
            echo(tmt.utils.format(
                self, step.get('summary') or '', key_color='blue'))
            # Show all or requested step attributes
            for key in keys or step:
                if key == 'summary':
                    continue
                try:
                    echo(tmt.utils.format(key, step[key]))
                except KeyError:
                    pass


class Plugin(tmt.utils.Common):
    """ Common parent of all step plugins """

    def __init__(self, data={}, step=None, name=None):
        """ Store plugin data """
        super(Plugin, self).__init__(name=name, parent=step)
        self.data = data
        self.step = step

    def go(self):
        """ Go and perform the plugin task """
        raise NotImplementedError

    def dump(self):
        """ Dump current step plugin data """
        return self.data
