import os

import click
import fmf.utils

import tmt.base
import tmt.utils
from tmt.steps.discover import DiscoverPlugin
from tmt.steps.execute import ExecutePlugin
from tmt.steps.execute.internal import ExecuteInternal

STATUS_VARIABLE = 'IN_PLACE_UPGRADE'
BEFORE_UPGRADE_SUFFIX = 'old'
DURING_UPGRADE_SUFFIX = 'upgrade'
AFTER_UPGRADE_SUFFIX = 'new'
UPGRADES_DIRECTORY = 'upgrades'

SUPPORTED_DISCOVER_KEYS = ['how', 'ref', 'filter', 'exclude', 'tests']


class ExecuteUpgrade(ExecuteInternal):
    """
    Perform upgrades during testing.

    The upgrade executor runs the discovered tests (using the internal
    executor), then performs a set of upgrade tasks from a remote repository,
    and finally, re-runs the tests on the upgraded guest.

    The IN_PLACE_UPGRADE environment variable is set during the test execution
    to differentiate between the stages of the test. It is set to "old"
    during the first execution and "new" during the second execution.
    Test names are prefixed with this value to make the names unique.

    The upgrade tasks performing the actual system upgrade are taken from
    a remote repository based on an upgrade path (e.g. fedora35to36).
    The upgrade path must correspond to a plan name in the remote repository
    whose discover selects tests (upgrade tasks) performing the upgrade.
    Currently, selection of upgrade tasks in the remote repository can be done
    using both fmf and shell discover. The supported keys in discover are:
     - ref
     - filter
     - exclude
     - tests

    The environment variables defined in the remote upgrade path plan are
    passed to the upgrade tasks when they are executed. An example of an
    upgrade path (in the remote repository):

    discover: # Selects appropriate upgrade tasks (L1 tests)
        how: fmf
        filter: "tag:fedora"
    environment: # This is passed to upgrade tasks
        SOURCE: 35
        TARGET: 36
    execute:
        how: tmt

    The same options and config keys and values can be used as in the
    internal executor.

    Minimal execute config example:

        execute:
            how: upgrade
            url: https://github.com/teemtee/upgrade
            upgrade-path: fedora35to36

    """

    # Supported methods
    _methods = [
        tmt.steps.Method(name='upgrade', doc=__doc__, order=50),
        ]

    # Supported keys
    _keys = ['url', 'upgrade-path']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._upgrade_underway = False
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
        return options + super().options(how)

    @property
    def discover(self):
        # If we are in the second phase (upgrade), take tests from our fake
        # discover plugin.
        if self._upgrade_underway:
            return self._discover_upgrade
        else:
            return self.step.plan.discover

    def go(self, guest):
        """ Execute available tests """
        self._results = []
        # Inform about the how, skip the actual execution
        super(ExecutePlugin, self).go()

        url = self.get('url')
        if not url:
            raise tmt.utils.ExecuteError(
                "URL to repository with upgrade tasks must be specified.")
        upgrade_path = self.get('upgrade-path')
        if not upgrade_path:
            raise tmt.utils.ExecuteError(
                "Upgrade path must be specified.")
        self.info('url', url, 'green')
        self.info('upgrade-path', upgrade_path, 'green')

        # Nothing to do in dry mode
        if self.opt('dry'):
            self._results = []
            return

        self._run_test_phase(guest, BEFORE_UPGRADE_SUFFIX)
        self._perform_upgrade(guest)
        self._run_test_phase(guest, AFTER_UPGRADE_SUFFIX)

    def _get_plan(self, upgrades_repo):
        """ Get plan based on upgrade path """
        tree = tmt.base.Tree(upgrades_repo)
        plans = tree.plans(names=[self.get('upgrade-path')])
        if len(plans) == 0:
            raise tmt.utils.ExecuteError("No matching upgrade path found.")
        elif len(plans) > 1:
            names = [plan.name for plan in plans]
            raise tmt.utils.ExecuteError(
                f"Ambiguous upgrade path reference, found plans "
                f"{fmf.utils.listed(names)}")
        return plans[0]

    def _perform_upgrade(self, guest):
        """ Perform a system upgrade """
        self.info('progress', 'performing upgrade', color='cyan')
        try:
            self._upgrade_underway = True
            upgrades = os.path.join(self.workdir, UPGRADES_DIRECTORY)
            self.run(
                ['git', 'clone', self.get('url'), upgrades],
                env={'GIT_ASKPASS': 'echo'})
            # Create a fake discover from the data in the upgrade path
            plan = self._get_plan(upgrades)
            data = plan.discover.data
            if isinstance(data, list):
                if len(data) > 1:
                    raise tmt.utils.ExecuteError(
                        "Multiple discover configs are not supported.")
                data = data[0]
            data = {k: v for k, v in data.items()
                    if k in SUPPORTED_DISCOVER_KEYS}
            # Force name
            data['name'] = 'upgrade_discover'
            # Override the path so that the correct tree is copied
            data['path'] = upgrades
            self._discover_upgrade = DiscoverPlugin.delegate(self.step, data)
            # Make it quiet
            quiet = self._discover_upgrade._context.params['quiet']
            try:
                self._discover_upgrade._context.params['quiet'] = True
                self._discover_upgrade.wake()
                self._discover_upgrade.go()
            finally:
                self._discover_upgrade._context.params['quiet'] = quiet
            for test in self._discover_upgrade.tests():
                test.name = f'/{DURING_UPGRADE_SUFFIX}/{test.name.lstrip("/")}'
            # Pass in the path-specific env variables
            self._run_tests(guest, extra_env=plan.environment)
        finally:
            self._discover_upgrade = None
            self._upgrade_underway = False

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

        self._run_tests(guest, extra_env={STATUS_VARIABLE: prefix})

        tests = self.discover.tests()
        for i, test in enumerate(tests):
            test.name = names_backup[i]
