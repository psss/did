import click
import fmf.utils

import tmt.base
import tmt.utils
from tmt.steps.discover import DiscoverPlugin
from tmt.steps.discover.fmf import DiscoverFmf
from tmt.steps.execute import ExecutePlugin
from tmt.steps.execute.internal import ExecuteInternal

STATUS_VARIABLE = 'IN_PLACE_UPGRADE'
BEFORE_UPGRADE_PREFIX = 'old'
DURING_UPGRADE_PREFIX = 'upgrade'
AFTER_UPGRADE_PREFIX = 'new'
UPGRADE_DIRECTORY = 'upgrade'

SUPPORTED_REMOTE_DISCOVER_KEYS = ['how', 'filter', 'test', 'exclude', 'tests']
INHERIT_FROM_DISCOVER = ['ref', 'test', 'filter', 'exclude']


class ExecuteUpgrade(ExecuteInternal):
    """
    Perform system upgrade during testing.

    The upgrade executor runs the discovered tests (using the internal
    executor), then performs a set of upgrade tasks from a remote
    repository, and finally, re-runs the tests on the upgraded guest.

    The IN_PLACE_UPGRADE environment variable is set during the test
    execution to differentiate between the stages of the test. It is set
    to "old" during the first execution and "new" during the second
    execution. Test names are prefixed with this value to make the names
    unique.

    The upgrade tasks performing the actual system upgrade are taken
    from a remote repository either based on an upgrade path
    (e.g. fedora35to36) or filters. The upgrade path must correspond to
    a plan name in the remote repository whose discover step selects
    tests (upgrade tasks) performing the upgrade. Currently, selection
    of upgrade tasks in the remote repository can be done using both fmf
    and shell discover method. The supported keys in discover are:

      - ref
      - filter
      - exclude
      - tests
      - test

    The environment variables defined in the remote upgrade path plan are
    passed to the upgrade tasks when they are executed. An example of an
    upgrade path plan (in the remote repository):

        discover: # Selects appropriate upgrade tasks (L1 tests)
            how: fmf
            filter: "tag:fedora"
        environment: # This is passed to upgrade tasks
            SOURCE: 35
            TARGET: 36
        execute:
            how: tmt

    If no upgrade path is specified in the plan, the tests (upgrade tasks)
    are selected based on the configuration of the upgrade plugin
    (e.g. based on the filter in its configuration).

    If these two possible ways of specifying upgrade tasks are combined,
    the remote discover plan is used but its options are overridden
    with the values specified locally.

    The same options and config keys and values can be used as in the
    internal executor.

    Minimal execute config example with an upgrade path:

        execute:
            how: upgrade
            url: https://github.com/teemtee/upgrade
            upgrade-path: /paths/fedora35to36

    Execute config example without an upgrade path:

        execute:
            how: upgrade
            url: https://github.com/teemtee/upgrade
            filter: "tag:fedora"
    """

    # Supported methods
    _methods = [
        tmt.steps.Method(name='upgrade', doc=__doc__, order=50),
        ]

    # Supported keys
    _keys = ['url', 'upgrade-path'] + INHERIT_FROM_DISCOVER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._discover_upgrade = None

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for given method """
        options = []
        options.append(click.option(
            '--url', '-u', metavar='REPOSITORY',
            help='URL of the git repository with upgrade tasks.'))
        options.append(click.option(
            '--upgrade-path', '-p', metavar='PLAN_NAME',
            help='Upgrade path corresponding to a plan name in the repository '
                 'with upgrade tasks.'))
        options.extend([DiscoverFmf.REF_OPTION, DiscoverFmf.TEST_OPTION,
                        DiscoverFmf.FILTER_OPTION, DiscoverFmf.EXCLUDE_OPTION])
        return options + super().options(how)

    @property
    def discover(self):
        """ Return discover plugin instance """
        # If we are in the second phase (upgrade), take tests from our fake
        # discover plugin.
        if self._discover_upgrade:
            return self._discover_upgrade
        else:
            return self.step.plan.discover

    def go(self, guest):
        """ Execute available tests """
        self._results = []
        # Inform about the how, skip the actual execution
        super(ExecutePlugin, self).go(guest)

        self.url = self.get('url')
        self.upgrade_path = self.get('upgrade-path')
        if not self.url:
            raise tmt.utils.ExecuteError(
                "URL to repository with upgrade tasks must be specified.")
        for key in self._keys:
            value = self.get(key)
            if value:
                if key == "test":
                    self.info('test', fmf.utils.listed(value), 'green')
                else:
                    self.info(key, value, color='green')

        # Nothing to do in dry mode
        if self.opt('dry'):
            self._results = []
            return

        self.verbose(
            'upgrade', 'run tests on the old system', color='blue', shift=1)
        self._run_test_phase(guest, BEFORE_UPGRADE_PREFIX)
        self.verbose(
            'upgrade', 'perform the system upgrade', color='blue', shift=1)
        self._perform_upgrade(guest)
        self.verbose(
            'upgrade', 'run tests on the new system', color='blue', shift=1)
        self._run_test_phase(guest, AFTER_UPGRADE_PREFIX)

    def _get_plan(self, upgrades_repo):
        """ Get plan based on upgrade path """
        tree = tmt.base.Tree(upgrades_repo)
        plans = tree.plans(names=[self.upgrade_path])
        if len(plans) == 0:
            raise tmt.utils.ExecuteError(
                f"No matching upgrade path found for '{self.upgrade_path}'.")
        elif len(plans) > 1:
            names = [plan.name for plan in plans]
            raise tmt.utils.ExecuteError(
                f"Ambiguous upgrade path reference, found plans "
                f"{fmf.utils.listed(names)}.")
        return plans[0]

    def _fetch_upgrade_tasks(self):
        """ Fetch upgrade tasks using DiscoverFmf """
        data = self.data.copy()
        data['how'] = 'fmf'
        data['name'] = 'upgrade-discover'
        self._discover_upgrade = DiscoverFmf(self.step, data)
        self._run_discover_upgrade()

    def _run_discover_upgrade(self):
        """ Silently run discover upgrade """
        # Make it quiet, we do not want any output from discover
        quiet = self._discover_upgrade._context.params['quiet']
        try:
            self._discover_upgrade._context.params['quiet'] = True
            # Discover normally uses also options from global Test class
            # (e.g. test -n foo). Ignore this when selecting upgrade tasks.
            tmt.base.Test.ignore_class_options = True
            self._discover_upgrade.wake()
            self._discover_upgrade.go()
        finally:
            self._discover_upgrade._context.params['quiet'] = quiet
            tmt.base.Test.ignore_class_options = False

    def _prepare_remote_discover_data(self, plan):
        """ Merge remote discover data with the local filters """
        data = plan.discover.data
        if isinstance(data, list):
            if len(data) > 1:
                raise tmt.utils.ExecuteError(
                    "Multiple discover configs are not supported.")
            data = data[0]
        result = {key: value for key, value in data.items()
                  if key in SUPPORTED_REMOTE_DISCOVER_KEYS}
        # Local values have priority, override
        for key in self._keys:
            value = self.get(key)
            if key in SUPPORTED_REMOTE_DISCOVER_KEYS and value:
                result[key] = value
        return result

    def _perform_upgrade(self, guest):
        """ Perform a system upgrade """
        try:
            self._fetch_upgrade_tasks()
            extra_environment = None
            if self.upgrade_path:
                # Create a fake discover from the data in the upgrade path
                plan = self._get_plan(self._discover_upgrade.testdir)
                data = self._prepare_remote_discover_data(plan)
                # Force name
                data['name'] = 'upgrade-discover-remote'
                # Override the path so that the correct tree is copied
                data['path'] = self._discover_upgrade.testdir
                self._discover_upgrade = DiscoverPlugin.delegate(
                    self.step, data)
                self._run_discover_upgrade()
                # Pass in the path-specific env variables
                extra_environment = plan.environment
            for test in self._discover_upgrade.tests():
                test.name = f'/{DURING_UPGRADE_PREFIX}/{test.name.lstrip("/")}'
            self._run_tests(guest, extra_environment=extra_environment)
        finally:
            self._discover_upgrade = None

    def _run_test_phase(self, guest, prefix):
        """
        Execute a single test phase on the guest

        Tests names are prefixed with the prefix argument in order to make
        their names unique so that the results are distinguishable.
        The prefix is also set as IN_PLACE_UPGRADE environment variable.
        """
        names_backup = []
        for test in self.discover.tests():
            names_backup.append(test.name)
            test.name = f'/{prefix}/{test.name.lstrip("/")}'

        self._run_tests(guest, extra_environment={STATUS_VARIABLE: prefix})

        tests = self.discover.tests()
        for i, test in enumerate(tests):
            test.name = names_backup[i]
