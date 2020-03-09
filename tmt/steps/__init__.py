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
        self._status = None

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

    @property
    def enabled(self):
        """ True if the step is enabled """
        try:
            return self.name in self.plan.run._context.obj.steps
        except AttributeError:
            return None

    def status(self, status=None):
        """
        Get and set current step status

        The meaning of the status is as follows:
        todo ... config, data and command line processed (we know what to do)
        done ... the final result of the step stored to workdir (we are done)
        """
        # Update status
        if status is not None:
            # Check for valid values
            if status not in ['todo', 'done']:
                raise GeneralError(f"Invalid status '{status}'.")
            # Show status only if changed
            elif self._status != status:
                self._status = status
                self.debug('status', status, color='yellow')
        # Return status
        return self._status

    def load(self):
        """ Load status and step data from the workdir """
        try:
            content = tmt.utils.yaml_to_dict(self.read('step.yaml'))
            self.debug('Successfully loaded step data.')
            self.data = content['data']
            self.status(content['status'])
        except GeneralError:
            self.debug('Step data not found.')

    def save(self):
        """ Save status and step data to the workdir """
        content = dict(status=self.status(), data=self.data)
        self.write('step.yaml', tmt.utils.dict_to_yaml(content))

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        # Cleanup possible old workdir if called with --force
        if self.opt('force'):
            self._workdir_cleanup()

        # Load stored data
        self.load()

        # Status 'todo' means the step has not finished successfully.
        # Probably interrupted in the middle. Clean up the work
        # directory to give it another chance with a fresh start.
        if self.status() == 'todo':
            self.debug("Step has not finished. Let's try once more!")
            self._workdir_cleanup()

        # Nothing more to do when the step is already done
        if self.status() == 'done':
            return

        # Override step data with command line options
        how = self.opt('how')
        if how is not None:
            for data in self.data:
                    data['how'] = how

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

    def wake(self):
        """ Wake up the plugin (override data with command line) """

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
