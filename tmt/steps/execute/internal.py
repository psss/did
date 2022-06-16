import os
import sys
import time

import click

import tmt
import tmt.steps.execute
import tmt.utils
from tmt.steps.execute import TEST_OUTPUT_FILENAME, Script

# Script handling reboots, in restraint compatible fashion
TMT_REBOOT_SCRIPT = Script("/usr/local/bin/tmt-reboot",
                           aliases=[
                               "/usr/local/bin/rstrnt-reboot",
                               "/usr/local/bin/rhts-reboot"],
                           related_variables=[
                               "TMT_REBOOT_COUNT",
                               "REBOOTCOUNT",
                               "RSTRNT_REBOOTCOUNT"]
                           )

# Script for archiving a file, usable for BEAKERLIB_COMMAND_SUBMIT_LOG
TMT_FILE_SUBMIT_SCRIPT = Script("/usr/local/bin/tmt-file-submit")

# File for requesting reboot
REBOOT_REQUEST_FILENAME = "reboot_request"

# List of all available scripts
SCRIPTS = (TMT_FILE_SUBMIT_SCRIPT, TMT_REBOOT_SCRIPT)


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

    # Supported keys
    _keys = ["script", "interactive"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_progress_message = ""
        self.scripts = SCRIPTS

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
        # Disable interactive progress bar
        options.append(click.option(
            '--no-progress-bar', is_flag=True,
            help='Disable interactive progress bar showing the current test.'))
        return options + super().options(how)

    def wake(self, keys=None):
        """ Wake up the plugin, process data, apply options """
        super().wake(keys=keys)
        # Make sure that script is a list
        tmt.utils.listify(self.data, keys=['script'])

    # TODO: consider switching to utils.updatable_message() - might need more
    # work, since use of _show_progress is split over several methods.
    def _show_progress(self, progress, test_name, finish=False):
        """
        Show an interactive progress bar in non-verbose mode.

        If the output is not an interactive terminal, or progress bar is
        disabled using an option, just output the message as info without
        utilising \r. If finish is True, overwrite the previous progress bar.
        """
        # Verbose mode outputs other information, using \r to
        # create a status bar wouldn't work.
        if self.opt('verbose'):
            return

        # No progress if terminal not attached or explicitly disabled
        if not sys.stdout.isatty() or self.opt('no-progress-bar'):
            return

        # For debug mode show just an info message (unless finishing)
        message = f"{test_name} [{progress}]" if not finish else ""
        if self.opt('debug'):
            if not finish:
                self.info(message, shift=1)
            return

        # Show progress bar in an interactive shell.
        # We need to completely override the previous message, add
        # spaces if necessary.
        message = message.ljust(len(self._previous_progress_message))
        self._previous_progress_message = message
        message = self._indent('progress', message, color='cyan')
        sys.stdout.write(f"\r{message}")
        if finish:
            # The progress has been overwritten, return back to the start
            sys.stdout.write("\r")
            self._previous_progress_message = ""
        sys.stdout.flush()

    def _test_environment(self, test, extra_environment):
        """ Return test environment """
        data_directory = self.data_path(test, full=True, create=True)

        environment = extra_environment.copy()
        environment.update(test.environment)
        environment["TMT_TREE"] = self.parent.plan.worktree
        environment["TMT_TEST_DATA"] = os.path.join(
            data_directory, tmt.steps.execute.TEST_DATA)
        environment["TMT_REBOOT_REQUEST"] = os.path.join(
            data_directory,
            tmt.steps.execute.TEST_DATA,
            REBOOT_REQUEST_FILENAME)
        # Set all supported reboot variables
        for reboot_variable in TMT_REBOOT_SCRIPT.related_variables:
            environment[reboot_variable] = str(test._reboot_count)
        # Variables related to beakerlib tests
        if test.framework == 'beakerlib':
            environment['BEAKERLIB_DIR'] = data_directory
            environment['BEAKERLIB_COMMAND_SUBMIT_LOG'] = (
                f"bash {TMT_FILE_SUBMIT_SCRIPT.path}")

        return environment

    def execute(self, test, guest, progress, extra_environment):
        """ Run test on the guest """
        # Provide info/debug message
        self._show_progress(progress, test.name)
        self.verbose(
            'test', test.summary or test.name, color='cyan', shift=1, level=2)
        self.debug(f"Execute '{test.name}' as a '{test.framework}' test.")

        # Test will be executed in it's own directory, relative to the workdir
        workdir = os.path.join(self.discover.workdir, test.path.lstrip('/'))
        self.debug(f"Use workdir '{workdir}'.", level=3)

        # Create data directory, prepare test environment
        environment = self._test_environment(test, extra_environment)

        # Prepare the test command (use default options for shell tests)
        if test.framework == "shell":
            command = f"{tmt.utils.SHELL_OPTIONS}; {test.test}"
        else:
            command = test.test

        # Prepare custom function to log output in verbose mode
        def log(key, value=None, color=None, shift=1, level=1):
            self.verbose(key, value, color, shift=2, level=3)

        # Execute the test, save the output and return code
        timeout = ''
        start = time.time()
        try:
            stdout, stderr = guest.execute(
                command, cwd=workdir, env=environment,
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
            stdout or '', mode='a', level=3)
        test.real_duration = self.test_duration(start, end)
        duration = click.style(test.real_duration, fg='cyan')
        shift = 1 if self.opt('verbose') < 2 else 2
        self.verbose(
            f"{duration} {test.name} [{progress}]{timeout}", shift=shift)

    def check(self, test):
        """ Check the test result """
        self.debug(f"Check result of '{test.name}'.")
        if test.framework == 'beakerlib':
            return self.check_beakerlib(test)
        else:
            return self.check_shell(test)

    def _handle_reboot(self, test, guest):
        """
        Reboot the guest if the test requested it.

        Check for presence of a file signalling reboot request
        and orchestrate the reboot if it was requested. Also increment
        REBOOTCOUNT variable, reset it to 0 if no reboot was requested
        (going forward to the next test). Return whether reboot was done.
        """
        test_data = os.path.join(
            self.data_path(test, full=True), tmt.steps.execute.TEST_DATA)
        reboot_request_path = os.path.join(test_data, REBOOT_REQUEST_FILENAME)
        if os.path.exists(reboot_request_path):
            test._reboot_count += 1
            self.debug(f"Reboot during test '{test}' "
                       f"with reboot count {test._reboot_count}.")
            with open(reboot_request_path, 'r') as reboot_file:
                reboot_command = reboot_file.read().strip()
            # Reset the file
            os.remove(reboot_request_path)
            guest.push(test_data)
            try:
                guest.reboot(command=reboot_command)
            except tmt.utils.RunError:
                self.fail(
                    f"Failed to reboot guest using the "
                    f"custom command '{reboot_command}'.")
                raise
            except tmt.utils.ProvisionError:
                self.warn(
                    "Guest does not support soft reboot, "
                    "trying hard reboot.")
                guest.reboot(hard=True)
            return True
        return False

    def go(self, guest):
        """ Execute available tests """
        super().go()
        self._results = []

        # Nothing to do in dry mode
        if self.opt('dry'):
            self._results = []
            return

        self._run_tests(guest)

    def _run_tests(self, guest, extra_environment=None):
        """ Execute tests on provided guest """
        extra_environment = extra_environment or {}

        # Prepare tests and helper scripts, check options
        tests = self.prepare_tests()
        exit_first = self.get('exit-first', default=False)

        # Prepare scripts, except localhost guest
        if not guest.localhost:
            self.prepare_scripts(guest)

        # Push workdir to guest and execute tests
        guest.push()
        # We cannot use enumerate here due to continue in the code
        index = 0
        while index < len(tests):
            test = tests[index]
            if not hasattr(test, "_reboot_count"):
                test._reboot_count = 0
            self.execute(
                test, guest, progress=f"{index + 1}/{len(tests)}",
                extra_environment=extra_environment)

            # Pull test logs from the guest, exclude beakerlib backups
            if test.framework == "beakerlib":
                exclude = [
                    "--exclude",
                    self.data_path(test, "backup*", full=True)]
            else:
                exclude = None
            guest.pull(
                source=self.data_path(test, full=True),
                extend_options=exclude)

            # Handle reboot, check results
            if self._handle_reboot(test, guest):
                continue
            self._results.append(self.check(test))
            if (exit_first and
                    self._results[-1].result not in ('pass', 'info')):
                # Clear the progress bar before outputting
                self._show_progress('', '', True)
                self.warn(
                    f'Test {test.name} failed, stopping execution.')
                break
            index += 1
        # Overwrite the progress bar, the test data is irrelevant
        self._show_progress('', '', True)

        # Pull artifacts created in the plan data directory
        self.debug("Pull the plan data directory.", level=2)
        guest.pull(source=self.step.plan.data_directory)

    def results(self):
        """ Return test results """
        return self._results

    def requires(self):
        """ Return list of required packages """
        # FIXME Remove when we drop support for the old execution methods
        return ['beakerlib'] if self.step._framework == 'beakerlib' else []
