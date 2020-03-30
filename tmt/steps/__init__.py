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
        super().__init__(name=name, parent=plan)
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


class Method(object):
    """ Step implementation method """

    def __init__(self, name, summary, order):
        """ Store method data """
        self.name = name
        self.summary = summary
        self.order = order

    def describe(self):
        """ Format name and summary for a nice method overview """
        return f'{self.name} '.ljust(22, '.') + f' {self.summary}'


class PluginIndex(type):
    """ Plugin metaclass used to register all available plugins """

    def __init__(cls, name, bases, attributes):
        """ Store all defined methods in the parent class """
        try:
            for method in cls._methods:
                # Store reference to the implementing class
                method.class_ = cls
                # Add to the list of supported methods in parent class
                bases[0]._supported_methods.append(method)
        except AttributeError:
            pass


class Plugin(tmt.utils.Common, metaclass=PluginIndex):
    """ Common parent of all step plugins """

    # List of all supported methods aggregated from all plugins
    _supported_methods = []

    def __init__(self, step, data):
        """ Store plugin name, data and parent step """

        # Ensure that plugin data contains name
        if 'name' not in data:
            raise GeneralError("Missing 'name' in plugin data.")

        # Store name, data and parent step
        super().__init__(parent=step, name=data['name'])
        self.data = data
        self.step = step

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for given method """
        # Include common options supported across all plugins
        return tmt.options.verbose_debug_quiet + tmt.options.force_dry

    @classmethod
    def command(cls):
        """ Prepare click command for all supported methods """
        # Create one command for each supported method
        commands = {}
        usage = r'Supported methods:'
        for method in cls.methods():
            usage += f'\n{method.describe()}'
            command = cls.base_command(usage=method.summary)
            # Apply plugin specific options
            for option in method.class_.options(method.name):
                command = option(command)
            commands[method.name] = command

        # Create base command with common options using method class
        method_class = tmt.options.create_method_class(commands)
        command = cls.base_command(method_class, usage)
        # Apply common options
        for option in cls.options():
            command = option(command)
        return command

    @classmethod
    def methods(cls):
        """ Return all supported methods ordered by priority """
        return sorted(cls._supported_methods, key=lambda method: method.order)

    @classmethod
    def delegate(cls, how):
        """
        Return plugin class implementing given method

        Supports searching by method prefix as well (e.g. 'virtual').
        The first matching method with the lowest 'order' wins.
        """
        # Filter matching methods, pick the one with the lowest order
        for method in cls.methods():
            if method.name.startswith(how):
                return method.class_

        # Report invalid method
        raise tmt.utils.SpecificationError(f"Unsupported method '{how}'.")

    def default(self, option, default=None):
        """ Return default data for given option """
        return None

    def get(self, option, default=None):
        """ Get option from plugin data, user/system config or defaults """
        # Check plugin data first
        try:
            return self.data[option]
        except KeyError:
            pass

        # Check user config and system config
        # TODO

        # Finally check plugin defaults
        return self.default(option, default)

    def wake(self):
        """ Wake up the plugin (override data with command line) """
        raise NotImplementedError

    def go(self):
        """ Go and perform the plugin task """
        # Show the method
        self.info('how', self.data['how'], 'green')
        # Show name only if there are more steps
        if self.name != 'one':
            self.info('name', self.name, 'green')
