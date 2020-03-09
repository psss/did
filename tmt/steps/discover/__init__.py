# coding: utf-8

""" Discover Step Classes """

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
        self.write('run.yaml', tmt.utils.dict_to_yaml(tests))

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super(Discover, self).wake()

        # Check execute step for possible shell scripts
        scripts = self.plan.execute.opt(
            'script', self.plan.execute.data[0].get('script'))
        if scripts:
            if isinstance(scripts, str):
                scripts = [scripts]
            tests = []
            for index in range(len(scripts)):
                name = f'script-{str(index).zfill(2)}'
                tests.append(dict(name=name, test=scripts[index]))
            # Append new data if tests already defined
            if self.data[0].get('tests'):
                self.data.append(
                    dict(how='shell', tests=tests, name='execute'))
            # Otherwise override current empty definition
            else:
                self.data[0]['tests'] = tests

        # Choose the right plugin and wake it up
        for data in self.data:
            if data['how'] == 'fmf':
                from tmt.steps.discover.fmf import DiscoverFmf
                plugin = DiscoverFmf(data, step=self)
            elif data['how'] == 'shell':
                from tmt.steps.discover.shell import DiscoverShell
                plugin = DiscoverShell(data, step=self)
            else:
                raise tmt.utils.SpecificationError(
                    f"Unknown discover method '{data['how']}'.")
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
        keys = ['how', 'repository', 'revision', 'filter']
        super(Discover, self).show(keys)

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


class DiscoverPlugin(tmt.steps.Plugin):
    """ Common parent of discover plugins """

    def __init__(self, data, step=None, name=None):
        """ Basic plugin initialization """
        super(DiscoverPlugin, self).__init__(data=data, step=step, name=name)

    def tests(self):
        """ Return discovered tests """
        raise NotImplementedError
