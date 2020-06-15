import os
import re
import fmf
import tmt
import shutil
import click
import tmt.steps.discover

# Regular expressions for beakerlib libraries
LIBRARY_REGEXP = re.compile(r'^library\(([^/]+)(/[^)]+)\)$')

# Default beakerlib libraries location and destination directory
DEFAULT_REPOSITORY = 'https://github.com/beakerlib'
DEFAULT_DESTINATION = 'libs'


class LibraryError(Exception):
    """ Used when library cannot be parsed from the identifier """


class Library(object):
    """ A beakerlib library """

    def __init__(self, identifier, parent):
        """ Process the library identifier and fetch the library """
        self.parent = parent

        # The 'library(repo/lib)' format
        if isinstance(identifier, str):
            identifier = identifier.strip()
            matched = LIBRARY_REGEXP.search(identifier)
            if not matched:
                raise LibraryError
            self.parent.debug(f"Detected library '{identifier}'.", level=3)
            self.format = 'rpm'
            self.repo, self.name = matched.groups()
            self.url = os.path.join(DEFAULT_REPOSITORY, self.repo)
            self.ref = 'master'
            self.destination = DEFAULT_DESTINATION
        # The fmf identifier
        elif isinstance(identifier, dict):
            self.parent.debug(f"Detected library '{identifier}'.", level=3)
            self.format = 'fmf'
            self.url = identifier.get('url')
            self.ref = identifier.get('ref', 'master')
            self.destination = identifier.get(
                'destination', DEFAULT_DESTINATION).lstrip('/')
            self.name = identifier.get('name', '/')
            if not self.name.startswith('/'):
                raise tmt.utils.DiscoverError(
                    f"Library name '{self.name}' does not start with a '/'.")
            # Use provided repository nick name or parse it from the url
            try:
                self.repo = identifier.get('nick') or re.search(
                    r'/([^/]+?)(/|\.git)?$', self.url).group(1)
            except AttributeError:
                raise tmt.utils.DiscoverError(
                    f"Unable to parse repository name from '{self.url}'.")
        # Something weird
        else:
            raise LibraryError

        # Fetch the library
        self.fetch()

    def __str__(self):
        """ Use repo/name for string representation """
        return f"{self.repo}{self.name}"

    def fetch(self):
        """ Fetch the library (unless already fetched) """
        # Check if the library was already fetched
        try:
            library = self.parent._libraries[self.repo]
            if library.url != self.url:
                raise tmt.utils.DiscoverError(
                    f"Library '{self.repo}' with url '{self.url}' conflicts "
                    f"with already fetched library from '{library.url}'.")
            if library.ref != self.ref:
                raise tmt.utils.DiscoverError(
                    f"Library '{self.repo}' using ref '{self.ref}' conflicts "
                    f"with already fetched library using ref '{library.ref}'.")
            self.parent.debug(f"Library '{self}' already fetched.", level=3)
            # Reuse the existing metadata tree
            self.tree = library.tree
        # Fetch the library and add it to the index
        except KeyError:
            self.parent.debug(f"Fetch library '{self}'.", level=3)
            # Prepare path, clone the repository, checkout ref
            directory = os.path.join(
                self.parent.workdir, self.destination, self.repo)
            # Clone repo with disabled prompt to ignore missing/private repos
            try:
                self.parent.run(
                    ['git', 'clone', self.url, directory],
                    shell=False, env={"GIT_TERMINAL_PROMPT": "0"})
            except tmt.utils.RunError as error:
                # Fallback to install during the prepare step if in rpm format
                if self.format == 'rpm':
                    raise LibraryError
                self.parent.info(
                    f"Failed to fetch library '{self}' from '{self.url}'.",
                    color='red')
                raise
            self.parent.run(
                ['git', 'checkout', self.ref], shell=False, cwd=directory)
            # Initialize metadata tree, add self into the library index
            self.tree = fmf.Tree(directory)
            self.parent._libraries[self.repo] = self

        # Get the library node, check require and recommend
        library = self.tree.find(self.name)
        if not library:
            raise tmt.utils.DiscoverError(
                f"Library '{self.name}' not found in '{self.repo}'.")
        self.require = tmt.utils.listify(library.get('require', []))
        self.recommend = tmt.utils.listify(library.get('recommend', []))


class DiscoverFmf(tmt.steps.discover.DiscoverPlugin):
    """
    Discover available tests from fmf metadata

    By default all available tests from the current repository are used
    so the minimal configuration looks like this:

        discover:
            how: fmf

    Full config example:

        discover:
            how: fmf
            url: https://github.com/psss/tmt
            ref: master
            path: /fmf/root
            test: /tests/basic
            filter: 'tier: 1'
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='fmf', doc=__doc__, order=50)]

    def __init__(self, data, plan):
        """ Initialize discover step data """
        super().__init__(data, plan)
        # Dictionary of fetched libraries indexed by repo name
        self._libraries = dict()

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for given method """
        return [
            click.option(
                '-u', '--url', metavar='REPOSITORY',
                help='URL of the git repository with fmf metadata.'),
            click.option(
                '-r', '--ref', metavar='REVISION',
                help='Branch, tag or commit specifying the git revision.'),
            click.option(
                '-p', '--path', metavar='ROOT',
                help='Path to the metadata tree root.'),
            click.option(
                '-t', '--test', metavar='NAMES', multiple=True,
                help='Select tests by name.'),
            click.option(
                '-F', '--filter', metavar='FILTERS', multiple=True,
                help='Include only tests matching the filter.'),
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return default data for given option """
        # Git revision defaults to master if url provided
        if option == 'ref' and self.get('url'):
            return 'master'
        # No other defaults available
        return default

    def show(self):
        """ Show discover details """
        super().show(['url', 'ref', 'path', 'test', 'filter'])

    def wake(self):
        """ Wake up the plugin (override data with command line) """

        # Handle backward-compatible stuff
        if 'repository' in self.data:
            self.data['url'] = self.data.pop('repository')
        if 'revision' in self.data:
            self.data['ref'] = self.data.pop('revision')

        # Make sure that 'filter' and 'test' keys are lists
        for key in ['filter', 'test']:
            if key in self.data and not isinstance(self.data[key], list):
                self.data[key] = [self.data[key]]

        # Process command line options, apply defaults
        for option in ['url', 'ref', 'path', 'test', 'filter']:
            value = self.opt(option)
            if value:
                self.data[option] = value

    def dependencies(self, all_requires):
        """
        Check dependencies for possible beakerlib libraries

        Fetch all identified libraries, check their required and
        recommended packages. Return tuple (requires, recommends)
        containing lists of regular rpm package names aggregated
        from all fetched libraries.
        """
        requires = []
        recommends = []
        for require in all_requires:
            # Library require
            try:
                library = Library(require, parent=self)
                recommends.extend(library.recommend)
                # Recursively check for possible dependent libraries
                require, recommend = self.dependencies(library.require)
                requires.extend(require)
                recommends.extend(recommend)
            # Regular package require
            except LibraryError:
                requires.append(require)
        return list(set(requires)), list(set(recommends))

    def go(self):
        """ Discover available tests """
        super(DiscoverFmf, self).go()

        # Check url and path, prepare test directory
        url = self.get('url')
        path = self.get('path')
        testdir = os.path.join(self.workdir, 'tests')

        # Clone provided git repository (if url given)
        if url:
            self.info('url', url, 'green')
            self.debug(f"Clone '{url}' to '{testdir}'.")
            self.run(['git', 'clone', url, testdir], shell=False)
        # Copy git repository root to workdir
        else:
            if path and not os.path.isdir(path):
                raise tmt.utils.DiscoverError(
                    f"Provided path '{path}' is not a directory.")
            fmf_root = path or self.step.plan.run.tree.root
            # Check git repository root (use fmf root if not found)
            try:
                output = self.run(
                    'git rev-parse --show-toplevel', cwd=fmf_root, dry=True)
                git_root = output[0].strip('\n')
            except tmt.utils.RunError:
                self.debug(f"Git root not found, using '{fmf_root}.'")
                git_root = fmf_root
            # Set path to relative path from the git root to fmf root
            path = os.path.relpath(fmf_root, git_root)
            self.info('directory', git_root, 'green')
            self.debug(f"Copy '{git_root}' to '{testdir}'.")
            if not self.opt('dry'):
                shutil.copytree(git_root, testdir)

        # Checkout revision if requested
        ref = self.get('ref')
        if ref:
            self.info('ref', ref, 'green')
            self.debug(f"Checkout ref '{ref}'.")
            self.run(['git', 'checkout', '-f', ref], cwd=testdir, shell=False)

        # Adjust path and optionally show
        if path is None or path == '.':
            path = ''
        else:
            self.info('path', path, 'green')

        # Prepare the whole tree path and test path prefix
        tree_path = os.path.join(testdir, path.lstrip('/'))
        if not os.path.isdir(tree_path) and not self.opt('dry'):
            raise tmt.utils.DiscoverError(
                f"Metadata tree path '{path}' not found.")
        prefix_path = os.path.join('/tests', path.lstrip('/'))

        # Show filters and test names if provided
        filters = self.get('filter', [])
        for filter_ in filters:
            self.info('filter', filter_, 'green')
        names = self.get('test', [])
        if names:
            self.info('names', fmf.utils.listed(names), 'green')

        # Initialize the metadata tree, search for available tests
        self.debug(f"Check metadata tree in '{tree_path}'.")
        if self.opt('dry'):
            self._tests = []
            return
        self._tests = tmt.Tree(tree_path).tests(filters=filters, names=names)

        # Prefix tests and handle library requires
        for test in self._tests:
            # Prefix test path with 'tests' and possible 'path' prefix
            test.path = os.path.join(prefix_path, test.path.lstrip('/'))
            # Check for possible required beakerlib libraries
            if test.require:
                requires, recommends = self.dependencies(test.require)
                # Update test requires to regular rpm packages only
                test.require = requires
                # Extend recommended packages with possible library recommends
                test.recommend = list(set(test.recommend + recommends))

    def tests(self):
        """ Return all discovered tests """
        return self._tests
