import tmt
import tmt.steps
import tmt.steps.discover

# See the online documentation for more details about writing plugins
# https://tmt.readthedocs.io/en/stable/plugins.html


@tmt.steps.provides_method('example')
class DiscoverExample(tmt.steps.discover.DiscoverPlugin):
    """
    A concise summary of what the plugin does

    Here goes the detailed plugin description which is displayed
    in the --help message. It is recommended to include a couple
    of configuration examples as well.
    """

    def show(self):
        """ Show plugin details for given or all available keys """
        super().show([])
        print("show() called")

    def wake(self):
        """
        Wake up the plugin (override data with command line)

        If a list of option names is provided, their value will be
        checked and stored in self.data unless empty or undefined.
        """
        print("wake() called")

        # Check provided tests, default to an empty list
        if 'tests' not in self.data:
            self.data['tests'] = []
        self._tests = []

    def go(self):
        """
        Go and perform the plugin task

        Discover available tests in this case.
        """
        super().go()
        print("go() called")

        # Prepare test environment
        print("Code should prepare environment for tests.")

        # Discover available tests
        self._tests = tmt.Tree(logger=self._logger, path=".").tests()

    def tests(self):
        """
        Return discovered tests.

        Each DiscoverPlugin has to implement this method.
        Should return a list of Test() objects.
        """
        return self._tests
