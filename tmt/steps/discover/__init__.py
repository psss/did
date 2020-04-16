# coding: utf-8

""" Discover Step Classes """

import click
import tmt
from fmf.utils import listed

class Discover(tmt.steps.Step):
    """ Gather and show information about test cases to be executed """

    def __init__(self, data, plan):
        """ Store supported attributes, check for sanity """
        super(Discover, self).__init__(data, plan)
        self.plugins = []

        # List of Test() objects representing discovered tests
        self._tests = []

    def load(self):
        """ Load step data from the workdir """
        super(Discover, self).load()
        try:
            tests = tmt.utils.yaml_to_dict(self.read('tests.yaml'))
            self._tests = [
                tmt.Test(data, name) for name, data in tests.items()]
        except tmt.utils.GeneralError:
            self.debug('Discovered tests not found.')

    def save(self):
        """ Save step data to the workdir """
        super(Discover, self).save()

        # Apply common plan environment to all tests
        environment = self.plan.environment

        # Create tests.yaml with the full test data
        tests = dict([
            (test.name, test.export(format_='dict', environment=environment))
            for test in self.tests()])
        self.write('tests.yaml', tmt.utils.dict_to_yaml(tests))

        # Create 'run.yaml' with the list of tests for the executor
        if not self.tests():
            return
        tests = dict([
            test.export(format_='execute', environment=environment)
            for test in self.tests()])
        self.write('run.yaml', tmt.utils.dict_to_yaml(tests, width=1000000))

    def _discover_from_execute(self):
        """ Check the execute step for possible shell script tests """

        # Check scripts for command line and data, convert to list if needed
        scripts = self.plan.execute.opt('script')
        if not scripts:
            scripts = self.plan.execute.data[0].get('script')
        if not scripts:
            return
        if isinstance(scripts, str):
            scripts = [scripts]

        # Prepare the list of tests
        tests = []
        for index, script in enumerate(scripts):
            name = f'script-{str(index).zfill(2)}'
            tests.append(dict(name=name, test=script))

        # Append new data if tests already defined
        if self.data[0].get('tests'):
            self.data.append(
                dict(how='shell', tests=tests, name='execute'))
        # Otherwise override current empty definition
        else:
            self.data[0]['tests'] = tests

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super(Discover, self).wake()

        # Check execute step for possible tests (unless already done)
        if self.status() is None:
            self._discover_from_execute()

        # Choose the right plugin and wake it up
        for data in self.data:
            plugin_class = DiscoverPlugin.delegate(data['how'])
            self.debug(
                f"Using '{plugin_class.__name__}' plugin "
                f"for the '{data['how']}' method.")
            plugin = plugin_class(self, data)
            self.plugins.append(plugin)
            plugin.wake()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.debug('Discover wake up complete (already done before).')
        # Save status and step data (now we know what to do)
        else:
            self.status('todo')
            self.save()

    def show(self):
        """ Show discover details """
        keys = ['how', 'url', 'ref', 'path', 'test', 'filter']
        super().show(keys)

    def summary(self):
        """ Give a concise summary of the discovery """
        # Summary of selected tests
        text = listed(len(self.tests()), 'test') + ' selected'
        self.info('tests', text, 'green', shift=1)
        # Test list in verbose mode
        for test in self.tests():
            self.verbose(test.name, color='red', shift=2)

    def go(self):
        """ Execute all steps """
        super(Discover, self).go()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.info('status', 'done', 'green', shift=1)
            self.summary()
            return

        # Perform test discovery, gather discovered tests
        self._tests = []
        for plugin in self.plugins:
            # Go and discover tests
            plugin.go()
            # Prefix test name only if multiple plugins configured
            prefix = f'/{plugin.name}' if len(self.plugins) > 1 else ''
            # Check discovered tests, modify test name/path
            for test in plugin.tests():
                test.name = f"{prefix}{test.name}"
                test.path = f"/{plugin.name}{test.path}"
                self._tests.append(test)

        # Give a summary, update status and save
        self.summary()
        self.status('done')
        self.save()

    def tests(self):
        """ Return the list of all enabled tests """
        return [test for test in self._tests if test.enabled]

    def requires(self):
        """ Return all tests' requires """
        requires = set()
        for test in self.tests():
            for value in getattr(test, 'require', []):
                requires.add(value)
        return list(requires)


class DiscoverPlugin(tmt.steps.Plugin):
    """ Common parent of discover plugins """

    @classmethod
    def base_command(cls, method_class=None, usage=None):
        """ Create base click command (common for all discover plugins) """

        # Prepare help message
        message = 'Gather information about test cases to be executed.'
        if usage is not None:
            message += '\n\n\b\n' + usage

        # Create the command
        @click.command(cls=method_class, help=message)
        @click.pass_context
        @click.option(
            '-h', '--how', metavar='METHOD',
            help='Use specified method to discover tests.')
        def discover(context, **kwargs):
            context.obj.steps.add('discover')
            Discover._save_context(context)

        return discover

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for given method """
        return super().options(how)

    def tests(self):
        """
        Return discovered tests

        Each DiscoverPlugin has to implement this method.
        Should return a list of Test() objects.
        """
        raise NotImplementedError
