""" Handle BeakerLib Libraries """

import re
import os

import fmf
import tmt

# Regular expressions for beakerlib libraries
LIBRARY_REGEXP = re.compile(r'^library\(([^/]+)(/[^)]+)\)$')

# Default beakerlib libraries location and destination directory
DEFAULT_REPOSITORY = 'https://github.com/beakerlib'
DEFAULT_DESTINATION = 'libs'


class LibraryError(Exception):
    """ Used when library cannot be parsed from the identifier """


class Library(object):
    """
    A beakerlib library

    Takes care of fetching beakerlib libraries from remote repositories
    based on provided library identifier described in detail here:
    https://tmt.readthedocs.io/en/latest/spec/tests.html#require

    Optional 'parent' object inheriting from tmt.utils.Common can be
    provided in order to share the cache of already fetched libraries.

    The following attributes are available in the object:

    repo ........ library prefix (git repository name or nick if provided)
    name ........ library suffix (folder containing the library code)

    url ......... full git repository url
    ref ......... git revision (branch, tag or commit)
    dest ........ target folder into which the library repo is cloned

    tree ........ fmf tree holding library metadata
    require ..... list of required packages
    recommend ... list of recommended packages

    Libraries are fetched into the 'libs' directory under parent's
    workdir or into 'destination' if provided in the identifier.
    """

    def __init__(self, identifier, parent=None):
        """ Process the library identifier and fetch the library """
        # Use an empty common class if parent not provided (for logging, cache)
        self.parent = parent or tmt.utils.Common(workdir=True)

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
            self.dest = DEFAULT_DESTINATION

        # The fmf identifier
        elif isinstance(identifier, dict):
            self.parent.debug(f"Detected library '{identifier}'.", level=3)
            self.format = 'fmf'
            self.url = identifier.get('url')
            self.ref = identifier.get('ref', 'master')
            self.dest = identifier.get(
                'destination', DEFAULT_DESTINATION).lstrip('/')
            self.name = identifier.get('name', '/')
            if not self.name.startswith('/'):
                raise tmt.utils.SpecificationError(
                    f"Library name '{self.name}' does not start with a '/'.")
            # Use provided repository nick name or parse it from the url
            try:
                self.repo = identifier.get('nick') or re.search(
                    r'/([^/]+?)(/|\.git)?$', self.url).group(1)
            except AttributeError:
                raise tmt.utils.GeneralError(
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
        # Initialize library cache (indexed by the repository name)
        if not hasattr(self.parent, '_library_cache'):
            self.parent._library_cache = dict()

        # Check if the library was already fetched
        try:
            library = self.parent._library_cache[self.repo]
            if library.url != self.url:
                raise tmt.utils.GeneralError(
                    f"Library '{self.repo}' with url '{self.url}' conflicts "
                    f"with already fetched library from '{library.url}'.")
            if library.ref != self.ref:
                raise tmt.utils.GeneralError(
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
                self.parent.workdir, self.dest, self.repo)
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
            self.parent._library_cache[self.repo] = self

        # Get the library node, check require and recommend
        library = self.tree.find(self.name)
        if not library:
            raise tmt.utils.GeneralError(
                f"Library '{self.name}' not found in '{self.repo}'.")
        self.require = tmt.utils.listify(library.get('require', []))
        self.recommend = tmt.utils.listify(library.get('recommend', []))


def dependencies(original_require, original_recommend=None, parent=None):
    """
    Check dependencies for possible beakerlib libraries

    Fetch all identified libraries, check their required and recommended
    packages. Return tuple (requires, recommends, libraries) containing
    list of regular rpm package names aggregated from all fetched
    libraries, list of aggregated recommended packages and a list of
    gathered libraries (instances of the Library class).
    """
    # Initialize lists, use set for require & recommend
    processed_require = set()
    processed_recommend = set(original_recommend or [])
    gathered_libraries = []

    for require in original_require:
        # Library require
        try:
            library = Library(require, parent=parent)
            gathered_libraries.append(library)
            # Recursively check for possible dependent libraries
            requires, recommends, libraries = dependencies(
                library.require, library.recommend, parent)
            processed_require.update(set(requires))
            processed_recommend.update(set(recommends))
            gathered_libraries.extend(libraries)
        # Regular package require
        except LibraryError:
            processed_require.add(require)

    # Convert to list and return the results
    processed_require = list(processed_require)
    processed_recommend = list(processed_recommend)
    return processed_require, processed_recommend, gathered_libraries
