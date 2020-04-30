import os
import re
import tmt
import shutil
import click

# Simple runner script name
RUNNER = 'run.sh'


class ExecuteSimple(tmt.steps.execute.ExecutePlugin):
    """ Execute tests using the simple executor """

    _shell_doc = """
    Execute shell tests using the simple executor

    A simple 'run.sh' script is run directly on the guest, executes all
    tests in one batch and checks the exit code for the test results.
    """

    _beakerlib_doc = """
    Execute beakerlib tests using the simple executor

    A simple 'run.sh' script is run directly on the guest, executes all
    tests in one batch and checks the beakerlib journal for the test
    results.
    """

    # Supported methods
    _methods = [
        tmt.steps.Method(
            name='shell.simple', doc=_shell_doc, order=50),
        tmt.steps.Method(
            name='beakerlib.simple', doc=_beakerlib_doc, order=50),
        ]

    # Test runner logs
    logs = ['stdout.log', 'stderr.log', 'nohup.out', 'results.yaml']

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for given method """
        options = []
        if how == 'shell.simple':
            options.append(click.option(
                '-s', '--script', metavar='SCRIPT', multiple=True,
                help='Shell script to be executed as a test.'))
        return options + super().options(how)

    def show(self):
        """ Show discover details """
        super().show(['script'])

    def wake(self):
        """ Wake up the plugin (override data with command line) """

        # Make sure that 'script' is a list
        tmt.utils.listify(self.data, keys=['script'])

        # Process command line options, apply defaults
        for option in ['script']:
            value = self.opt(option)
            if value:
                self.data[option] = value

    def prepare_runner(self):
        """ Place the runner script to workdir """
        # Detect location of the runner and copy it to workdir
        script_path = os.path.join(os.path.dirname(__file__), RUNNER)
        self.debug(f"Copy '{script_path}' to '{self.step.workdir}'.", level=2)
        shutil.copy(script_path, self.step.workdir)

        # Push the runner to guests
        for guest in self.step.plan.provision.guests():
            guest.push()

    def get_logs(self):
        """ Get logs contents, also print them to info() """
        # Pull the workdir changes
        for guest in self.step.plan.provision.guests():
            guest.pull()
        # Check each log, show in verbose mode
        for log in self.logs:
            try:
                output = self.step.read(log)
                self.verbose(log, output.strip(), 'yellow', level=2)
            except tmt.utils.FileError:
                pass

    def remove_logs(self, logs=[]):
        """ Clean up possible old logs """
        for log in self.logs:
            path = os.path.join(self.step.workdir, log)
            if os.path.exists(path):
                os.remove(path)

    def check_shell(self, test):
        """ Check result of a shell test """
        # Prepare log path
        data = {'log': f"results{test.name}/out.log"}
        # Process the exit code
        data['result'] = 'error'
        try:
            exit_code_file = f"results{test.name}/exitcode.log"
            exit_code = self.step.read(exit_code_file).strip()
            if exit_code == '0':
                data['result'] = 'pass'
            elif exit_code == '1':
                data['result'] = 'fail'
        except tmt.utils.FileError:
            log.debug(f"Exit code not found for test '{test.name}'.", level=3)
        return tmt.Result(data, test.name)

    def check_beakerlib(self, test):
        """ Check result of a beakerlib test """
        # Initialize data, prepare log paths
        data = {'result': 'error', 'log': []}
        logs = ['out.log', 'journal.txt', 'journal_colored.txt']
        for log in logs:
            path = f"results{test.name}/{log}"
            if os.path.isfile(os.path.join(self.step.workdir, path)):
                data['log'].append(path)
        # Check beakerlib log for the result
        try:
            beakerlib_results_file = f"results{test.name}/TestResults"
            results = self.step.read(beakerlib_results_file)
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

    def go(self):
        """ Execute available tests """
        super().go()

        # Nothing to do in dry mode
        if self.opt('dry'):
            self._results = []
            return

        # Prepare the runner and remove logs
        self.remove_logs()
        self.prepare_runner()

        # Run the runner
        try:
            how = 'beakerlib' if 'beakerlib' in self.get('how') else 'shell'
            for guest in self.step.plan.provision.guests():
                guest.execute(
                    f'./{RUNNER} -v .. {how} stdout.log stderr.log',
                    cwd=self.step.workdir)
        except tmt.utils.RunError as error:
            self.get_logs()
            raise tmt.utils.ExecuteError(f'Test execution failed: {error}')
        self.get_logs()

        # Check test results
        self._results = []
        for test in self.step.plan.discover.tests():
            if how == 'beakerlib':
                self._results.append(self.check_beakerlib(test))
            else:
                self._results.append(self.check_shell(test))

    def results(self):
        """ Return test results """
        return self._results

    def requires(self):
        """ Return list of required packages """
        return ['beakerlib'] if 'beakerlib' in self.get('how') else []
