import os
import fmf
import tmt
import copy
import click
import shutil
import tmt.steps.discover

class DiscoverShell(tmt.steps.discover.DiscoverPlugin):
    """
    Use provided list of shell script tests

    List of test cases to be executed can be defined manually directly
    in the plan as a list of dictionaries containing test name, actual
    test script and optionally a path to the test. Example config:

    discover:
        how: shell
        tests:
        - name: /help/main
          test: tmt --help
        - name: /help/test
          test: tmt test --help
        - name: /help/smoke
          test: ./smoke.sh
          path: /tests/shell
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='shell', doc=__doc__, order=50)]

    def show(self):
        """ Show config details """
        super().show([])
        tests = self.get('tests')
        if tests:
            test_names = [test['name'] for test in tests]
            click.echo(tmt.utils.format('tests', test_names))

    def wake(self):
        # Check provided tests, default to an empty list
        if 'tests' not in self.data:
            self.data['tests'] = []
        self._tests = []

    def go(self):
        """ Discover available tests """
        super(DiscoverShell, self).go()
        tests = fmf.Tree(dict(summary='tests'))

        # Check and process each defined shell test
        for data in self.data['tests']:
            # Create data copy (we want to keep original data for save()
            data = copy.deepcopy(data)
            # Extract name, make sure it is present
            try:
                name = data.pop('name')
            except KeyError:
                raise tmt.utils.SpecificationError(
                    f"Missing test name in '{self.step.plan.name}'.")
            # Make sure that the test script is defined
            if 'test' not in data:
                raise tmt.utils.SpecificationError(
                    f"Missing test script in '{self.step.plan.name}'.")
            # Prepare path to the test working directory (tree root by default)
            try:
                data['path'] = f"/tests{data['path']}"
            except KeyError:
                data['path'] = f"/tests"
            # Apply default test duration unless provided
            if not 'duration' in data:
                data['duration'] = tmt.base.DEFAULT_TEST_DURATION_L2

            # Create a simple fmf node, adjust its name
            tests.child(name, data)

        # Copy directory tree (if defined) to the workdir
        directory = self.step.plan.run.tree.root
        testdir = os.path.join(self.workdir, 'tests')
        if directory:
            self.info('directory', directory, 'green')
            self.debug("Copy '{}' to '{}'.".format(directory, testdir))
            shutil.copytree(directory, testdir, symlinks=True)
        else:
            os.makedirs(testdir)

        # Use a tmt.Tree to apply possible command line filters
        tests = tmt.Tree(tree=tests).tests()
        self._tests = tests

    def tests(self):
        return self._tests
