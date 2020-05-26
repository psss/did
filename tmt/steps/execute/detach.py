import os
import tmt
import shutil
import click

# Simple runner script name
RUNNER = 'run.sh'

# Test runner logs
LOGS = ['stdout.log', 'stderr.log', 'nohup.out', 'results.yaml']


class ExecuteSimple(tmt.steps.execute.ExecutePlugin):
    """ Run tests using a detached shell script on the guest """

    _shell_doc = """
    Run shell tests using a detached script on the guest

    A simple 'run.sh' script is run directly on the guest, executes all
    tests in one batch and checks the exit code for the test results.
    """

    _beakerlib_doc = """
    Run beakerlib tests using a detached script on the guest

    A simple 'run.sh' script is run directly on the guest, executes all
    tests in one batch and checks the beakerlib journal for the test
    results.
    """

    # Supported methods
    _methods = [
        tmt.steps.Method(
            name='shell.detach', doc=_shell_doc, order=50),
        tmt.steps.Method(
            name='beakerlib.detach', doc=_beakerlib_doc, order=50),
        ]

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

        # Store the method for future use
        self.beakerlib = 'beakerlib' in self.get('how')

    def prepare_runner(self):
        """ Place the runner script to workdir """
        # Detect location of the runner and copy it to workdir
        script_path = os.path.join(os.path.dirname(__file__), RUNNER)
        self.debug(f"Copy '{script_path}' to '{self.step.workdir}'.", level=2)
        shutil.copy(script_path, self.step.workdir)

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

    def remove_logs(self, logs=[]):
        """ Clean up possible old logs """
        for log in LOGS:
            path = os.path.join(self.step.workdir, log)
            if os.path.exists(path):
                os.remove(path)

    def check(self, test):
        """ Check the test result """
        if self.beakerlib:
            return self.check_beakerlib(test)
        else:
            # Get the exit code from the file
            try:
                exit_code_file = self.log(test, 'exitcode.log')
                test.returncode = int(self.step.read(exit_code_file).strip())
            except tmt.utils.FileError:
                self.debug(f"Exit code not found for '{test.name}'.", level=3)
                test.returncode = None
            return self.check_shell(test)

    def go(self):
        """ Execute available tests """
        super().go()
        self._results = []

        # Nothing to do in dry mode
        if self.opt('dry'):
            return

        # Prepare the runner and remove logs
        self.remove_logs()
        self.prepare_runner()

        # For each guest execute all tests
        for guest in self.step.plan.provision.guests():

            # Push workdir to guest and execute tests
            guest.push()
            try:
                how = 'beakerlib' if self.beakerlib else 'shell'
                guest.execute(
                    f'./{RUNNER} -v .. {how} stdout.log stderr.log',
                    cwd=self.step.workdir)
            except tmt.utils.RunError as error:
                guest.pull()
                self.info('error', 'Test execution failed.', color='red')
                self.check_output(error)
                raise

            # Pull logs from guest, show logs and check results
            guest.pull()
            self.show_logs()
            for test in self.step.plan.discover.tests():
                self._results.append(self.check(test))

    def results(self):
        """ Return test results """
        return self._results

    def requires(self):
        """ Return list of required packages """
        return ['beakerlib'] if self.beakerlib else []
