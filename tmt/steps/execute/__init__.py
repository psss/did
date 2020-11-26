import os
import re
import fmf
import tmt
import click

# Test data directory name
TEST_DATA = 'data'

# Default test framework
DEFAULT_FRAMEWORK = 'shell'

# The main test output filename
TEST_OUTPUT_FILENAME = 'output.txt'


class Execute(tmt.steps.Step):
    """
    Run tests using the specified executor.

    Note that the old execution methods 'shell.tmt', 'beakerlib.tmt',
    'shell.detach' and 'beakerlib.detach' have been deprecated and the
    backward-compatible support for them will be dropped in March 2021.

    Use the new L1 metadata attribute 'framework' instead to specify
    which test framework should be used for execution. This allows to
    combine tests using different test frameworks in a single plan.
    """

    # Internal executor is the default implementation
    how = 'tmt'

    def __init__(self, data, plan):
        """ Initialize execute step data """
        super().__init__(data, plan)
        # List of Result() objects representing test results
        self._results = []

        # Default test framework and mapping old methods
        # FIXME remove when we drop the old execution methods
        self._framework = DEFAULT_FRAMEWORK
        # Map old methods now if there is no run (and thus no wake up)
        if not self.plan.run:
            self._map_old_methods()

    def load(self):
        """ Load test results """
        super().load()
        try:
            results = tmt.utils.yaml_to_dict(self.read('results.yaml'))
            self._results = [
                tmt.Result(data, test) for test, data in results.items()]
        except tmt.utils.FileError as error:
            self.debug('Test results not found.', level=2)

    def save(self):
        """ Save test results to the workdir """
        super().save()
        results = dict([
            (result.name, result.export()) for result in self.results()])
        self.write('results.yaml', tmt.utils.dict_to_yaml(results))

    def _map_old_methods(self):
        """ Map the old execute methods in a backward-compatible way """
        how = self.data[0]['how']
        matched = re.search(r"^(shell|beakerlib)(\.(tmt|detach))?$", how)
        if not matched:
            return
        # Show the old method deprecation warning to users
        self.warn(f"The '{how}' execute method has been deprecated.")
        # Map the old syntax to the appropriate executor
        # shell, beakerlib ---> tmt
        # shell.tmt, beakerlib.tmt ---> tmt
        # shell.detach, beakerlib.detach ---> detach
        how = matched.group(3) or 'tmt'
        self.warn(f"Use 'how: {how}' in the execute step instead (L2).")
        self.data[0]['how'] = how
        # Store shell or beakerlib as the default test framework
        # (used when the framework is not defined in the L1 metadata)
        framework = matched.group(1)
        self.warn(f"Set 'framework: {framework}' in test metadata (L1).")
        self._framework = framework
        self.warn("Support for old methods will be dropped in March 2021.")

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super().wake()

        # There should be just a single definition
        if len(self.data) > 1:
            raise tmt.utils.SpecificationError(
                "Multiple execute steps defined in '{}'.".format(self.plan))

        # Choose the right plugin and wake it up
        self._map_old_methods()
        executor = ExecutePlugin.delegate(self, self.data[0])
        executor.wake()
        self._plugins.append(executor)

        # Nothing more to do if already done
        if self.status() == 'done':
            self.debug(
                'Execute wake up complete (already done before).', level=2)
        # Save status and step data (now we know what to do)
        else:
            self.status('todo')
            self.save()

    def show(self):
        """ Show execute details """
        ExecutePlugin.delegate(self, self.data[0]).show()

    def summary(self):
        """ Give a concise summary of the execution """
        tests = fmf.utils.listed(self.results(), 'test')
        self.info('summary', f'{tests} executed', 'green', shift=1)

    def go(self):
        """ Execute tests """
        super().go()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.info('status', 'done', 'green', shift=1)
            self.summary()
            self.try_running_login()
            return

        # Make sure that guests are prepared
        if not self.plan.provision.guests():
            raise tmt.utils.ExecuteError("No guests available for execution.")

        # Execute the tests, store results
        for plugin in self.plugins():
            plugin.go()
            if isinstance(plugin, ExecutePlugin):
                self._results = plugin.results()

        # Give a summary, update status and save
        self.summary()
        self.status('done')
        self.save()

    def requires(self):
        """
        Packages required for test execution

        Return a list of packages which need to be installed on the
        guest so that tests can be executed. Used by the prepare step.
        """
        requires = set()
        for plugin in self.plugins(classes=ExecutePlugin):
            requires.update(plugin.requires())
        return list(requires)

    def results(self):
        """
        Results from executed tests

        Return a dictionary with test results according to the spec:
        https://tmt.readthedocs.io/en/latest/spec/steps.html#execute
        """
        return self._results


class ExecutePlugin(tmt.steps.Plugin):
    """ Common parent of execute plugins """

    # List of all supported methods aggregated from all plugins
    _supported_methods = []

    # Internal executor is the default implementation
    how = 'tmt'

    @classmethod
    def base_command(cls, method_class=None, usage=None):
        """ Create base click command (common for all execute plugins) """

        # Prepare general usage message for the step
        if method_class:
            usage = Execute.usage(method_overview=usage)

        # Create the command
        @click.command(cls=method_class, help=usage)
        @click.pass_context
        @click.option(
            '-h', '--how', metavar='METHOD',
            help='Use specified method for test execution.')
        def execute(context, **kwargs):
            context.obj.steps.add('execute')
            Execute._save_context(context)

        return execute

    def data_path(self, test, filename=None, full=False, create=False):
        """
        Prepare full/relative test data directory/file path

        Construct test data directory path for given test, create it
        if requested and return the full or relative path to it (if
        filename not provided) or to the given data file otherwise.
        """
        # Prepare directory path, create if requested
        directory = os.path.join(
            self.step.workdir, TEST_DATA, test.name.lstrip('/'))
        if create and not os.path.isdir(directory):
            os.makedirs(directory)
        if not filename:
            return directory
        path = os.path.join(directory, filename)
        return path if full else os.path.relpath(path, self.step.workdir)

    def prepare_tests(self):
        """
        Prepare discovered tests for testing

        Check which tests have been discovered, for each test prepare
        the aggregated metadata in a 'metadata.yaml' file under the test
        data directory and finally return a list of discovered tests.
        """
        tests = self.step.plan.discover.tests()
        for test in tests:
            metadata_filename = self.data_path(
                test, filename='metadata.yaml', full=True, create=True)
            self.write(
                metadata_filename, tmt.utils.dict_to_yaml(test._metadata))
        return tests

    def check_shell(self, test):
        """ Check result of a shell test """
        # Prepare the log path
        data = {'log': self.data_path(test, TEST_OUTPUT_FILENAME)}
        # Process the exit code
        try:
            data['result'] = {0: 'pass', 1: 'fail'}[test.returncode]
        except KeyError:
            data['result'] = 'error'
            # Add note about the exceeded duration
            if test.returncode == tmt.utils.PROCESS_TIMEOUT:
                data['note'] = 'timeout'
        return tmt.Result(data, test.name)

    def check_beakerlib(self, test):
        """ Check result of a beakerlib test """
        # Initialize data, prepare log paths
        data = {'result': 'error', 'log': []}
        for log in [TEST_OUTPUT_FILENAME, 'journal.txt']:
            if os.path.isfile(self.data_path(test, log, full=True)):
                data['log'].append(self.data_path(test, log))
        # Check beakerlib log for the result
        try:
            beakerlib_results_file = self.data_path(
                test, 'TestResults', full=True)
            results = self.read(beakerlib_results_file, level=3)
        except tmt.utils.FileError:
            self.debug(f"Unable to read '{beakerlib_results_file}'.", level=3)
            return tmt.Result(data, test.name)
        try:
            matched = re.search('TESTRESULT_RESULT_STRING=(.*)', results)
            result = matched.group(1)
        except AttributeError:
            self.debug(f"No result in '{beakerlib_results_file}'.", level=3)
            return tmt.Result(data, test.name)
        data['result'] = result.lower()
        return tmt.Result(data, test.name)
