import dataclasses
import json
import os
import sys
import time
from typing import Any, List, Optional

import click

import tmt
import tmt.options
import tmt.steps
import tmt.steps.execute
import tmt.utils
from tmt.base import Test
from tmt.result import Result, ResultOutcome
from tmt.steps.execute import (SCRIPTS, TEST_OUTPUT_FILENAME,
                               TMT_FILE_SUBMIT_SCRIPT, TMT_REBOOT_SCRIPT)
from tmt.steps.provision import Guest
from tmt.utils import EnvironmentType

TEST_WRAPPER_FILENAME = 'tmt-test-wrapper.sh'
TEST_WRAPPER_INTERACTIVE = '{remote_command}'
TEST_WRAPPER_NONINTERACTIVE = 'set -eo pipefail; {remote_command} </dev/null |& cat'


@dataclasses.dataclass
class ExecuteInternalData(tmt.steps.execute.ExecuteStepData):
    script: List[str] = dataclasses.field(default_factory=list)
    interactive: bool = False

    _normalize_script = tmt.utils.NormalizeKeysMixin._normalize_string_list


@tmt.steps.provides_method('tmt')
class ExecuteInternal(tmt.steps.execute.ExecutePlugin):
    """
    Use the internal tmt executor to execute tests

    The internal tmt executor runs tests on the guest one by one, shows
    testing progress and supports interactive debugging as well. Test
    result is based on the script exit code (for shell tests) or the
    results file (for beakerlib tests).
    """

    _data_class = ExecuteInternalData

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._previous_progress_message = ""
        self.scripts = SCRIPTS

    @classmethod
    def options(cls, how: Optional[str] = None) -> List[tmt.options.ClickOptionDecoratorType]:
        """ Prepare command line options for given method """
        return [
            click.option(
                '-s', '--script', metavar='SCRIPT', multiple=True,
                help='Shell script to be executed as a test.'),
            # Interactive mode
            click.option(
                '-i', '--interactive', is_flag=True,
                help='Run in interactive mode, do not capture output.'),
            # Disable interactive progress bar
            click.option(
                '--no-progress-bar', is_flag=True,
                help='Disable interactive progress bar showing the current test.')
            ] + super().options(how)

    # TODO: consider switching to utils.updatable_message() - might need more
    # work, since use of _show_progress is split over several methods.
    def _show_progress(self, progress: str, test_name: str,
                       finish: bool = False) -> None:
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

    def _test_environment(
            self,
            test: Test,
            extra_environment: Optional[EnvironmentType] = None) -> EnvironmentType:
        """ Return test environment """

        extra_environment = extra_environment or {}

        data_directory = self.data_path(test, full=True, create=True)

        environment = extra_environment.copy()
        environment.update(test.environment)
        assert self.parent is not None
        assert isinstance(self.parent, tmt.steps.execute.Execute)
        environment["TMT_TREE"] = self.parent.plan.worktree
        environment["TMT_TEST_DATA"] = os.path.join(
            data_directory, tmt.steps.execute.TEST_DATA)
        environment["TMT_REBOOT_REQUEST"] = os.path.join(
            data_directory,
            tmt.steps.execute.TEST_DATA,
            TMT_REBOOT_SCRIPT.created_file)
        # Set all supported reboot variables
        for reboot_variable in TMT_REBOOT_SCRIPT.related_variables:
            environment[reboot_variable] = str(test._reboot_count)
        # Variables related to beakerlib tests
        if test.framework == 'beakerlib':
            environment['BEAKERLIB_DIR'] = data_directory
            environment['BEAKERLIB_COMMAND_SUBMIT_LOG'] = (
                f"bash {TMT_FILE_SUBMIT_SCRIPT.path}")

        return environment

    def _test_output_logger(
            self,
            key: str,
            value: Optional[str] = None,
            color: Optional[str] = None,
            shift: int = 2,
            level: int = 3,
            err: bool = False) -> None:
        """ Custom logger for test output with shift 2 and level 3 defaults """
        self.verbose(key=key, value=value, color=color, shift=shift, level=level, err=err)

    def execute(self, test: Test, guest: Guest,
                extra_environment: Optional[EnvironmentType] = None) -> None:
        """ Run test on the guest """
        self.debug(f"Execute '{test.name}' as a '{test.framework}' test.")

        # Test will be executed in it's own directory, relative to the workdir
        assert self.discover.workdir is not None  # narrow type
        assert test.path is not None  # narrow type
        workdir = os.path.join(self.discover.workdir, test.path.lstrip('/'))
        self.debug(f"Use workdir '{workdir}'.", level=3)

        # Create data directory, prepare test environment
        environment = self._test_environment(test, extra_environment)

        test_wrapper_filepath = os.path.join(workdir, TEST_WRAPPER_FILENAME)

        # Prepare the test command (use default options for shell tests)
        if test.framework == "shell":
            test_command = f"{tmt.utils.SHELL_OPTIONS}; {test.test}"
        else:
            test_command = test.test
        self.debug('Test script', test_command, level=3)

        # Prepare the wrapper, push to guest
        self.write(test_wrapper_filepath, test_command, 'w')
        os.chmod(test_wrapper_filepath, 0o755)
        guest.push(
            source=test_wrapper_filepath,
            destination=test_wrapper_filepath,
            options=["-s", "-p", "--chmod=755"])

        # Prepare the actual remote command
        remote_command = f'./{TEST_WRAPPER_FILENAME}'
        if self.get('interactive'):
            remote_command = TEST_WRAPPER_INTERACTIVE.format(remote_command=remote_command)
        else:
            remote_command = TEST_WRAPPER_NONINTERACTIVE.format(remote_command=remote_command)

        # Execute the test, save the output and return code
        start = time.time()
        try:
            stdout, _ = guest.execute(
                remote_command,
                cwd=workdir,
                env=environment,
                join=True,
                interactive=self.get('interactive'),
                log=self._test_output_logger,
                timeout=tmt.utils.duration_to_seconds(test.duration),
                test_session=True,
                friendly_command=test.test)
            test.returncode = 0
        except tmt.utils.RunError as error:
            stdout = error.stdout
            test.returncode = error.returncode
            if test.returncode == tmt.utils.PROCESS_TIMEOUT:
                self.debug(f"Test duration '{test.duration}' exceeded.")
        end = time.time()
        self.write(
            self.data_path(test, TEST_OUTPUT_FILENAME, full=True),
            stdout or '', mode='a', level=3)
        test.real_duration = self.test_duration(start, end)

    def check(self, test: Test) -> List[Result]:
        """ Check the test result """
        self.debug(f"Check result of '{test.name}'.")
        if test.result == 'custom':
            return self.check_custom_results(test)
        if test.framework == 'beakerlib':
            return self.check_beakerlib(test)
        else:
            try:
                return self.check_result_file(test)
            except tmt.utils.FileError:
                return self.check_shell(test)

    def _will_reboot(self, test: Test) -> bool:
        """ True if reboot is requested """
        return os.path.exists(self._reboot_request_path(test))

    def _reboot_request_path(self, test: Test) -> str:
        """ Return reboot_request """
        reboot_request_path = os.path.join(
            self.data_path(test, full=True),
            tmt.steps.execute.TEST_DATA,
            TMT_REBOOT_SCRIPT.created_file)
        return reboot_request_path

    def _handle_reboot(self, test: Test, guest: Guest) -> bool:
        """
        Reboot the guest if the test requested it.

        Check for presence of a file signalling reboot request
        and orchestrate the reboot if it was requested. Also increment
        REBOOTCOUNT variable, reset it to 0 if no reboot was requested
        (going forward to the next test). Return whether reboot was done.
        """
        if self._will_reboot(test):
            test._reboot_count += 1
            self.debug(f"Reboot during test '{test}' "
                       f"with reboot count {test._reboot_count}.")
            reboot_request_path = self._reboot_request_path(test)
            test_data = os.path.join(
                self.data_path(test, full=True),
                tmt.steps.execute.TEST_DATA)
            with open(reboot_request_path, 'r') as reboot_file:
                reboot_data = json.loads(reboot_file.read())
            reboot_command = reboot_data.get('command')
            try:
                timeout = int(reboot_data.get('timeout'))
            except ValueError:
                timeout = None
            # Reset the file
            os.remove(reboot_request_path)
            guest.push(test_data)
            rebooted = False
            try:
                rebooted = guest.reboot(command=reboot_command, timeout=timeout)
            except tmt.utils.RunError:
                self.fail(
                    f"Failed to reboot guest using the "
                    f"custom command '{reboot_command}'.")
                raise
            except tmt.utils.ProvisionError:
                self.warn(
                    "Guest does not support soft reboot, "
                    "trying hard reboot.")
                rebooted = guest.reboot(hard=True, timeout=timeout)
            if not rebooted:
                raise tmt.utils.RebootTimeoutError("Reboot timed out.")
            return True
        return False

    def go(self, guest: Guest) -> None:
        """ Execute available tests """
        super().go(guest)
        self._results: List[Result] = []

        # Nothing to do in dry mode
        if self.opt('dry'):
            self._results = []
            return

        self._run_tests(guest)

    def _run_tests(
            self,
            guest: Guest,
            extra_environment: Optional[EnvironmentType] = None) -> None:
        """ Execute tests on provided guest """

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

            progress = f"{index + 1}/{len(tests)}"
            self._show_progress(progress, test.name)
            self.verbose(
                'test', test.summary or test.name, color='cyan', shift=1, level=2)

            self.execute(test, guest, extra_environment=extra_environment)

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

            results = self.check(test)  # Produce list of results
            assert test.real_duration is not None  # narrow type
            duration = click.style(test.real_duration, fg='cyan')
            shift = 1 if self.opt('verbose') < 2 else 2

            # Handle reboot, abort, exit-first
            if self._will_reboot(test):
                # Output before the reboot
                self.verbose(
                    f"{duration} {test.name} [{progress}]", shift=shift)
                try:
                    if self._handle_reboot(test, guest):
                        continue
                except tmt.utils.RebootTimeoutError:
                    for result in results:
                        result.result = ResultOutcome.ERROR
                        result.note = 'reboot timeout'
            abort = self.check_abort_file(test)
            if abort:
                for result in results:
                    # In case of aborted all results in list will be aborted
                    result.note = 'aborted'
            self._results.extend(results)
            for result in results:
                # If test duration information is missing, print 8 spaces to keep indention
                duration = click.style(result.duration, fg='cyan') if result.duration else 8 * ' '
                self.verbose(f"{duration} {result.show()} [{progress}]", shift=shift)
            if (abort or exit_first and
                    result.result not in (ResultOutcome.PASS, ResultOutcome.INFO)):
                # Clear the progress bar before outputting
                self._show_progress('', '', True)
                what_happened = "aborted" if abort else "failed"
                self.warn(
                    f'Test {test.name} {what_happened}, stopping execution.')
                break
            index += 1

            # Log into the guest after each executed test if "login
            # --test" option is provided
            if self._login_after_test:
                assert test.path is not None  # narrow type
                self._login_after_test.after_test(
                    result,
                    cwd=os.path.join(self.discover.workdir or "", test.path.lstrip('/')),
                    env=self._test_environment(test, extra_environment),
                    )
        # Overwrite the progress bar, the test data is irrelevant
        self._show_progress('', '', True)

        # Pull artifacts created in the plan data directory
        self.debug("Pull the plan data directory.", level=2)
        guest.pull(source=self.step.plan.data_directory)

    def results(self) -> List[Result]:
        """ Return test results """
        return self._results

    def requires(self) -> List[str]:
        """ Return list of required packages """
        return []
