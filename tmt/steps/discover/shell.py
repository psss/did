import copy
import os

import click
import fmf

import tmt
import tmt.steps.discover


class DiscoverShell(tmt.steps.discover.DiscoverPlugin):
    """
    Use provided list of shell script tests

    List of test cases to be executed can be defined manually directly
    in the plan as a list of dictionaries containing test name, actual
    test script and optionally a path to the test. Example config:

    discover:
        how: shell
        tests:
        - name: /help/main
          test: tmt --help
        - name: /help/test
          test: tmt test --help
        - name: /help/smoke
          test: ./smoke.sh
          path: /tests/shell

    For DistGit repo one can extract source tarball and use its code.
    It is extracted to TMT_SOURCE_DIR however no patches are applied
    (only source tarball is extracted).

    discover:
        how: shell
        dist-git-source: true
        tests:
        - name: /upstream
          test: cd $TMT_SOURCE_DIR/*/tests && make test
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='shell', doc=__doc__, order=50)]

    def show(self, keys=None):
        """ Show config details """
        super().show([])
        tests = self.get('tests')
        if tests:
            test_names = [test['name'] for test in tests]
            click.echo(tmt.utils.format('tests', test_names))

    def wake(self, keys=None):
        """ Wake up the plugin, process data, apply options """
        super().wake(keys=keys)
        # Check provided tests, default to an empty list
        if 'tests' not in self.data:
            self.data['tests'] = []
        self._tests = []

    def go(self):
        """ Discover available tests """
        super(DiscoverShell, self).go()
        tests = fmf.Tree(dict(summary='tests'))

        # dist-git related
        sourcedir = os.path.join(self.workdir, 'source')
        dist_git_source = self.get('dist-git-source', False)

        # Check and process each defined shell test
        for data in self.data['tests']:
            # Create data copy (we want to keep original data for save()
            data = copy.deepcopy(data)
            # Extract name, make sure it is present
            try:
                name = data.pop('name')
            except KeyError:
                raise tmt.utils.SpecificationError(
                    f"Missing test name in '{self.step.plan.name}'.")
            # Make sure that the test script is defined
            if 'test' not in data:
                raise tmt.utils.SpecificationError(
                    f"Missing test script in '{self.step.plan.name}'.")
            # Prepare path to the test working directory (tree root by default)
            try:
                data['path'] = f"/tests{data['path']}"
            except KeyError:
                data['path'] = "/tests"
            # Apply default test duration unless provided
            if 'duration' not in data:
                data['duration'] = tmt.base.DEFAULT_TEST_DURATION_L2
            # Add source dir path variable
            if dist_git_source:
                data.setdefault('environment', {})[
                    'TMT_SOURCE_DIR'] = sourcedir
            # Create a simple fmf node, adjust its name
            tests.child(name, data)

        # Symlink tests directory to the plan work tree
        testdir = os.path.join(self.workdir, "tests")
        relative_path = os.path.relpath(self.step.plan.worktree, self.workdir)
        os.symlink(relative_path, testdir)

        if dist_git_source:
            try:
                git_root = self.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=self.step.plan.my_run.tree.root,
                    dry=True)[0].strip('\n')
            except tmt.utils.RunError:
                raise tmt.utils.DiscoverError(
                    f"Directory '{self.step.plan.my_run.tree.root}' "
                    f"is not a git repository.")
            try:
                self.extract_distgit_source(
                    git_root, sourcedir, self.get('dist-git-type'))
            except Exception as error:
                raise tmt.utils.DiscoverError(
                    "Failed to process 'dist-git-source'.", original=error)

        # Use a tmt.Tree to apply possible command line filters
        tests = tmt.Tree(tree=tests).tests(conditions=["manual is False"])
        self._tests = tests

    def tests(self):
        return self._tests
