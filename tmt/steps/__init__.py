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
    def enabled(self):
        """ True if the step is enabled """
        try:
            return self.name in self.plan.run._context.obj.steps
        except AttributeError:
            return None

    def load(self):
        """ Load step data from the workdir """
        pass

    def save(self):
        """ Save step data to the workdir """
        self.write('steps.yaml', tmt.utils.dictionary_to_yaml(self.data))

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        # Check workdir for possible stored data
        self.load()

        # Override data with command line input
        for step in self.data:
            how = self.opt('how')
            if how:
                step['how'] = how

    def go(self):
        """ Execute the test step """
        # Show step header and how
        self.info(self.name, color='blue')
        # Show workdir in verbose mode
        self.debug('workdir', self.workdir, 'magenta')

    def show(self, keys=[]):
        """ Show step details """
        for step in self.data:
            # Show empty steps only in verbose mode
            if (set(step.keys()) == set(['how', 'name'])
                    and not self.opt('verbose')):
                continue
            # Step name (and optional header)
            echo(tmt.utils.format(
                self, step.get('summary') or '', key_color='blue'))
            # Show all or requested step attributes
            for key in keys or step:
                # Skip showing the default name
                if key == 'name' and step['name'] == 'one':
                    continue
                # Skip showing summary again
                if key == 'summary':
                    continue
                try:
                    echo(tmt.utils.format(key, step[key]))
                except KeyError:
                    pass


class Plugin(tmt.utils.Common):
    """ Common parent of all step plugins """

    def __init__(self, data, step=None, name=None):
        """ Store plugin data """
        super(Plugin, self).__init__(name=name, parent=step)
        self.data = data
        self.step = step

    def go(self):
        """ Go and perform the plugin task """
        # Show the method
        self.info('how', self.data['how'], 'green')
        # Show name only if there are more steps
        if self.name != 'one':
            self.info('name', self.name, 'green')

    def dump(self):
        """ Dump current step plugin data """
        return self.data
