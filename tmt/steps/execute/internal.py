import os
import time
import click

import tmt
from tmt.steps.execute import TEST_OUTPUT_FILENAME


class ExecuteInternal(tmt.steps.execute.ExecutePlugin):
    """
    Use the internal tmt executor to execute tests

    The internal tmt executor runs tests on the guest one by one, shows
    testing progress and supports interactive debugging as well. Test
    result is based on the script exit code (for shell tests) or the
    results file (for beakerlib tests).
    """

    # Supported methods
    _methods = [
        tmt.steps.Method(name='tmt', doc=__doc__, order=50),
        tmt.steps.Method(name='shell.tmt', doc=__doc__, order=80),
        tmt.steps.Method(name='beakerlib.tmt', doc=__doc__, order=80),
        ]

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for given method """
        options = []
        # Shell script as a test
        options.append(click.option(
            '-s', '--script', metavar='SCRIPT', multiple=True,
            help='Shell script to be executed as a test.'))
        # Interactive mode
        options.append(click.option(
            '-i', '--interactive', is_flag=True,
            help='Run in interactive mode, do not capture output.'))
        return options + super().options(how)

    def show(self):
        """ Show execute details """
        super().show(['script', 'interactive'])

    def wake(self):
        """ Wake up the plugin (override data with command line) """
        super().wake(options=['script', 'interactive'])
        # Make sure that script is a list
        tmt.utils.listify(self.data, keys=['script'])

    def execute(self, test, guest):
        """ Run test on the guest """
        # Provide info/debug message
        self.verbose(
            'test', test.summary or test.name, color='cyan', shift=1, level=2)
        self.debug(f"Execute '{test.name}' as a '{test.framework}' test.")

        # Test will be executed in the workdir
        workdir = os.path.join(
            self.step.plan.discover.workdir, test.path.lstrip('/'))
        self.debug(f"Use workdir '{workdir}'.", level=3)

        # Create data directory, prepare environment
        data_directory = self.data_path(test, full=True, create=True)
        environment = test.environment
        if test.framework == 'beakerlib':
            environment = environment.copy()
            environment['BEAKERLIB_DIR'] = data_directory

        # Prepare custom function to log output in verbose mode
        def log(key, value=None, color=None, shift=1, level=1):
            self.verbose(key, value, color, shift=2, level=3)

        # Execute the test, save the output and return code
        timeout = ''
        start = time.time()
        try:
            stdout = guest.execute(
                test.test, cwd=workdir, env=environment,
                join=True, interactive=self.get('interactive'), log=log,
                timeout=tmt.utils.duration_to_seconds(test.duration))
            test.returncode = 0
        except tmt.utils.RunError as error:
            stdout = error.stdout
            test.returncode = error.returncode
            if test.returncode == tmt.utils.PROCESS_TIMEOUT:
                timeout = ' (timeout)'
                self.debug(f"Test duration '{test.duration}' exceeded.")
        end = time.time()
        self.write(
            self.data_path(test, TEST_OUTPUT_FILENAME, full=True),
            stdout or '', level=3)
        duration = time.strftime("%H:%M:%S", time.gmtime(end - start))
        duration = click.style(duration, fg='cyan')
        shift = 1 if self.opt('verbose') < 2 else 2
        self.verbose(
            f"{duration} {test.name}{timeout}", color='cyan', shift=shift)

    def check(self, test):
        """ Check the test result """
        self.debug(f"Check result of '{test.name}'.")
        if test.framework == 'beakerlib':
            return self.check_beakerlib(test)
        else:
            return self.check_shell(test)

    def go(self):
        """ Execute available tests """
        super().go()
        self._results = []

        # Nothing to do in dry mode
        if self.opt('dry'):
            self._results = []
            return

        # For each guest execute all tests
        tests = self.prepare_tests()
        for guest in self.step.plan.provision.guests():

            # Push workdir to guest and execute tests
            guest.push()
            for test in tests:
                self.execute(test, guest)

            # Pull logs from guest and check results
            guest.pull()
            for test in tests:
                self._results.append(self.check(test))

    def results(self):
        """ Return test results """
        return self._results

    def requires(self):
        """ Return list of required packages """
        # FIXME Remove when we drop support for the old execution methods
        return ['beakerlib'] if self.step._framework == 'beakerlib' else []
