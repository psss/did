import contextlib
import os
import stat
import sys
import time

import click

import tmt
import tmt.utils
from tmt.steps.execute import TEST_OUTPUT_FILENAME
from tmt.steps.provision import DEFAULT_RSYNC_OPTIONS
from tmt.steps.provision.local import GuestLocal

REBOOT_VARIABLES = (
    "TMT_REBOOT_COUNT",
    "REBOOTCOUNT",
    "RSTRNT_REBOOTCOUNT")
REBOOT_SCRIPT_PATHS = (
    "/usr/local/bin/rstrnt-reboot",
    "/usr/local/bin/rhts-reboot",
    "/usr/local/bin/tmt-reboot")
REBOOT_REQUEST_FILENAME = "reboot_request"
REBOOT_SCRIPT = f"""\
#!/bin/sh
touch "$TMT_TEST_DATA/{REBOOT_REQUEST_FILENAME}"
"""
REBOOT_BACKUP_EXT = ".tmt.backup"
REBOOT_SETUP_NAME = "reboot_setup"
REBOOT_SETUP_SCRIPT = f"""\
#!/bin/sh
for file in {" ".join(REBOOT_SCRIPT_PATHS)}; do
    # Backup existing file, keep track of what has been backed-up
    if [ -e "$file" ]; then
        mv "$file" "$file{REBOOT_BACKUP_EXT}"
        echo "$file"
    fi
    cp "$1" "$file" && chmod +x "$file"
done
"""
REBOOT_TEARDOWN_NAME = "reboot_teardown"
REBOOT_TEARDOWN_SCRIPT = f"""\
#!/bin/sh
for file in {" ".join(REBOOT_SCRIPT_PATHS)}; do
    rm "$file"
done

# We pass back the backed up files
for file in "$@"; do
    mv "$file{REBOOT_BACKUP_EXT}" "$file"
done
"""
REBOOT_TEMPLATE_NAME = "reboot_template"

FILE_SUBMIT_SCRIPT = """\
#!/bin/sh
FILENAME="$2"
[ -d "$TMT_TEST_DATA" ] || mkdir -p "$TMT_TEST_DATA"
cp "$FILENAME" "$TMT_TEST_DATA"
echo "File $FILENAME stored to $TMT_TEST_DATA"
"""
FILE_SUBMIT_NAME = "tmt-file-submit"


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
        try:
            # We need to completely override the previous message, add
            # spaces if necessary.
            message = message.ljust(len(self._previous_progress_message))
        except AttributeError:
            # First iteration, previous message not set
            pass
        self._previous_progress_message = message
        message = self._indent('progress', message, color='cyan')
        sys.stdout.write(f"\r{message}")
        if finish:
            # The progress has been overwritten, return back to the start
            sys.stdout.write(f"\r")
        sys.stdout.flush()

    def execute(self, test, guest, progress):
        """ Run test on the guest """
        # Provide info/debug message
        self._show_progress(progress, test.name)
        self.verbose(
            'test', test.summary or test.name, color='cyan', shift=1, level=2)
        self.debug(f"Execute '{test.name}' as a '{test.framework}' test.")

        # Test will be executed in the workdir
        workdir = os.path.join(
            self.step.plan.discover.workdir, test.path.lstrip('/'))
        self.debug(f"Use workdir '{workdir}'.", level=3)

        # Create data directory, prepare environment
        data_directory = self.data_path(test, full=True, create=True)
        environment = test.environment.copy()
        environment["TMT_TREE"] = self.parent.plan.worktree
        environment["TMT_TEST_DATA"] = os.path.join(
            data_directory, tmt.steps.execute.TEST_DATA)
        # Set all supported reboot variables
        for reboot_variable in REBOOT_VARIABLES:
            environment[reboot_variable] = str(test._reboot_count)
        # Variables related to beakerlib tests
        if test.framework == 'beakerlib':
            environment['BEAKERLIB_DIR'] = data_directory
            environment['BEAKERLIB_COMMAND_SUBMIT_LOG'] = (
                f"bash {self.step.workdir}/{FILE_SUBMIT_NAME}")

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
            stdout = guest.execute(
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

    def _setup_reboot_script(self, guest):
        """ Set up reboot script on the guest. """
        def setup_file(filename, content):
            file_path = os.path.join(self.workdir, filename)
            with open(file_path, 'w') as template:
                template.write(content)
            # Make it executable, keep perms when pushing
            perms = os.stat(file_path)
            os.chmod(file_path, perms.st_mode | stat.S_IEXEC)
            return file_path

        template = setup_file(REBOOT_TEMPLATE_NAME, REBOOT_SCRIPT)
        setup = setup_file(REBOOT_SETUP_NAME, REBOOT_SETUP_SCRIPT)
        teardown = setup_file(REBOOT_TEARDOWN_NAME, REBOOT_TEARDOWN_SCRIPT)
        guest.push(self.workdir, options=DEFAULT_RSYNC_OPTIONS + ["-p"])
        return template, setup, teardown

    @contextlib.contextmanager
    def _setup_reboot(self, guest):
        """ Prepare the guest environment for potential reboot """
        # Ignore local provision
        if isinstance(guest, GuestLocal):
            yield
            return
        backed_up = []
        template, setup, teardown = None, None, None
        try:
            self.debug("Setup our reboot script implementations.", level=2)
            template, setup, teardown = self._setup_reboot_script(guest)
            try:
                stdout = guest.execute(f"\"{setup}\" \"{template}\"")[0]
                backed_up.extend(stdout.splitlines())
            except tmt.utils.RunError as error:
                if "Read-only file system" not in error.stderr:
                    raise error
            yield
        finally:
            self.debug("Remove our reboot script implementations.", level=2)
            # FIXME: This part may not be executed if connection to the guest
            #        drops in the middle and the guest may be left in an
            #        inconsistent state.
            if teardown:
                backed_up_files = " ".join(backed_up)
                guest.execute(f"\"{teardown}\" {backed_up_files}")

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
            # Reset the file
            os.remove(reboot_request_path)
            guest.push(test_data)
            try:
                guest.reboot()
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

        # Prepare tests and helper scripts, check options
        tests = self.prepare_tests()
        exit_first = self.get('exit-first', default=False)
        self.step.write(FILE_SUBMIT_NAME, FILE_SUBMIT_SCRIPT)

        with self._setup_reboot(guest):
            # Push workdir to guest and execute tests
            guest.push()
            index = 0
            while index < len(tests):
                test = tests[index]
                if not hasattr(test, "_reboot_count"):
                    test._reboot_count = 0
                self.execute(
                    test, guest, progress=f"{index + 1}/{len(tests)}")
                guest.pull(source=self.data_path(test, full=True))
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
