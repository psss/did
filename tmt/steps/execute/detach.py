import os
import shutil
import time

import click

import tmt

# Simple runner script name
RUNNER = 'run.sh'

# Test runner logs
LOGS = ['stdout.log', 'stderr.log', 'nohup.out', 'results.yaml']


class ExecuteDetach(tmt.steps.execute.ExecutePlugin):
    """
    Run tests using a detached shell script on the guest

    A simple 'run.sh' script is run directly on the guest, executes all
    tests in one batch and checks for the test results using the exit
    code (for shell tests) or the results file (for beakerlib tests).
    """

    # Supported methods
    _methods = [
        tmt.steps.Method(name='detach', doc=__doc__, order=60),
        tmt.steps.Method(name='shell.detach', doc=__doc__, order=90),
        tmt.steps.Method(name='beakerlib.detach', doc=__doc__, order=90),
        ]

    # Supported keys
    _keys = ["script"]

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for given method """
        options = []
        options.append(click.option(
            '-s', '--script', metavar='SCRIPT', multiple=True,
            help='Shell script to be executed as a test.'))
        return options + super().options(how)

    def wake(self, keys=None):
        """ Wake up the plugin, process data, apply options """
        super().wake(keys=keys)
        # Make sure that 'script' is a list
        tmt.utils.listify(self.data, keys=['script'])

    def prepare_runner(self):
        """ Place the runner script to workdir """
        # Detect location of the runner and copy it to workdir
        script_path = os.path.join(os.path.dirname(__file__), RUNNER)
        self.debug(f"Copy '{script_path}' to '{self.step.workdir}'.", level=2)
        shutil.copy(script_path, self.step.workdir)
        # We're shipping the script as not-runnable. Make it runnable now.
        runner_path = os.path.join(self.step.workdir, RUNNER)
        os.chmod(runner_path, 0o0755)

    def show_logs(self):
        """ Check each log, show in verbose mode """
        for log in LOGS:
            try:
                output = self.step.read(log)
                self.verbose(log, output.strip(), 'yellow', level=2)
            except tmt.utils.FileError:
                pass

    def check_output(self, error):
        """ Add run.sh output to the raised exception """
        for output in ['stdout', 'stderr']:
            try:
                content = self.step.read(f"{output}.log")
                if content:
                    content = f"{getattr(error, output)}\nrun.sh:\n{content}"
                    setattr(error, output, content)
            except tmt.utils.FileError:
                pass

    def remove_logs(self):
        """ Clean up possible old logs """
        for log in LOGS:
            path = os.path.join(self.step.workdir, log)
            if os.path.exists(path):
                os.remove(path)

    def check(self, test):
        """ Check the test result """
        try:
            exit_code_file = self.data_path(test, 'exitcode.log')
            test.returncode = int(self.step.read(exit_code_file).strip())
        except tmt.utils.FileError:
            self.debug(f"Exit code not found for '{test.name}'.", level=3)
            test.returncode = None
        if test.framework == 'beakerlib':
            return self.check_beakerlib(test)
        else:
            return self.check_shell(test)

    def executed_test_count(self):
        """ Get the number of executed tests """
        stdout = self.step.read('stdout.log')
        # There is letter 'D' at the end marking done, subtract it
        return len(stdout.strip()) - 1

    def go(self, guest):
        """ Execute available tests """
        super().go()
        self._results = []

        # Nothing to do in dry mode
        if self.opt('dry'):
            return

        # Remove old logs, prepare the runner and tests
        self.remove_logs()
        self.prepare_runner()
        self.prepare_tests()

        # For each guest execute all tests
        exit_first = ' -x' if self.get('exit-first', default=False) else ''
        # Push workdir to guest and execute tests
        guest.push()
        start = time.time()
        try:
            guest.execute(
                f'./{RUNNER} -v{exit_first} .. stdout.log stderr.log',
                cwd=self.step.workdir)
        except tmt.utils.RunError as error:
            guest.pull()
            self.info('error', 'Test execution failed.', color='red')
            self.check_output(error)
            raise
        end = time.time()
        # Pull logs from guest, show logs and check results
        guest.pull(source=self.step.plan.execute.workdir)
        guest.pull(source=self.step.plan.data_directory)
        self.show_logs()
        # If --exit-first is used, not all tests may have been executed.
        # run.sh writes a letter F/. (Fail/pass) to stdout for each test.
        # Check results only of the executed tests.
        executed = self.executed_test_count()
        for i, test in enumerate(self.step.plan.discover.tests()):
            if i >= executed:
                self.warn('Not all tests have been executed.')
                break
            test.real_duration = self.test_duration(start, end)
            self._results.append(self.check(test))

    def results(self):
        """ Return test results """
        return self._results

    def requires(self):
        """ Return list of required packages """
        # FIXME Remove when we drop support for the old execution methods
        return ['beakerlib'] if self.step._framework == 'beakerlib' else []
