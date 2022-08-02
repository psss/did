""" Handle BeakerLib Libraries """

import os
import re
import shutil
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Tuple, Union, cast

import fmf

import tmt
import tmt.utils

# A beakerlib indetified type, can be a string or a dictionary
BeakerlibIdentifierType = Union[str, Dict[str, str]]
ImportedIdentifiersType = Optional[List[BeakerlibIdentifierType]]

# A type for Beakerlib dependencies
LibraryDependenciesType = Tuple[
    List[str], List[str], List['Library']
    ]

# Regular expressions for beakerlib libraries
LIBRARY_REGEXP = re.compile(r'^library\(([^/]+)(/[^)]+)\)$')

# Default beakerlib libraries location and destination directory
DEFAULT_REPOSITORY = 'https://github.com/beakerlib'
DEFAULT_DESTINATION = 'libs'

# List of git forges for which the .git suffix should be stripped
STRIP_SUFFIX_FORGES = [
    'https://github.com',
    'https://gitlab.com',
    'https://pagure.io',
    ]


class CommonWithLibraryCache(tmt.utils.Common):
    _library_cache: Dict[str, 'Library']


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

    def __init__(
            self,
            identifier: BeakerlibIdentifierType,
            parent: Optional[tmt.utils.Common] = None
            ) -> None:
        """ Process the library identifier and fetch the library """
        # Use an empty common class if parent not provided (for logging, cache)
        self.parent = parent or tmt.utils.Common(workdir=True)

        # Default branch is detected from the origin after cloning
        self.default_branch: Optional[str] = None

        self.identifier: BeakerlibIdentifierType
        # The 'library(repo/lib)' format
        if isinstance(identifier, str):
            identifier = identifier.strip()
            self.identifier = identifier
            matched = LIBRARY_REGEXP.search(identifier)
            if not matched:
                raise LibraryError
            self.parent.debug(f"Detected library '{identifier}'.", level=3)
            self.format: str = 'rpm'
            self.repo: str = matched.groups()[0]
            self.name: str = matched.groups()[1]
            self.url: Optional[str] = os.path.join(
                DEFAULT_REPOSITORY, self.repo)
            self.path: Optional[str] = None
            self.ref: Optional[str] = None
            self.dest: str = DEFAULT_DESTINATION

        # The fmf identifier
        elif isinstance(identifier, dict):
            self.identifier = identifier
            self.parent.debug(f"Detected library '{identifier}'.", level=3)
            self.format = 'fmf'
            self.url = identifier.get('url')
            self.path = identifier.get('path')
            # Strip possible trailing slash from path
            if isinstance(self.path, str):
                self.path = self.path.rstrip('/')
            if not self.url and not self.path:
                raise tmt.utils.SpecificationError(
                    "Need 'url' or 'path' to fetch a beakerlib library.")
            # Strip the '.git' suffix from url for known forges
            if self.url:
                for forge in STRIP_SUFFIX_FORGES:
                    if (self.url.startswith(forge)
                            and self.url.endswith('.git')):
                        self.url = self.url.rstrip('.git')
            self.ref = identifier.get('ref', None)
            self.dest = identifier.get(
                'destination', DEFAULT_DESTINATION).lstrip('/')
            self.name = identifier.get('name', '/')
            if not self.name.startswith('/'):
                raise tmt.utils.SpecificationError(
                    f"Library name '{self.name}' does not start with a '/'.")

            # Use provided repository nick name or parse it from the url/path
            repo = identifier.get('nick')
            if repo:
                if not isinstance(repo, str):
                    raise tmt.utils.SpecificationError(
                        f"Invalid library nick '{repo}', should be a string.")
            else:
                if self.url:
                    repo_search = re.search(r'/([^/]+?)(/|\.git)?$', self.url)
                    if not repo_search:
                        raise tmt.utils.GeneralError(
                            f"Unable to parse repository name from '{self.url}'.")
                    repo = repo_search.group(1)
                else:
                    # Either url or path must be defined
                    assert self.path is not None
                    try:
                        repo = os.path.basename(self.path)
                        if not repo:
                            raise TypeError
                    except TypeError:
                        raise tmt.utils.GeneralError(
                            f"Unable to parse repository name from '{self.path}'.")
            self.repo = repo

        # Something weird
        else:
            raise LibraryError

        # Fetch the library
        try:
            self.fetch()
        except fmf.utils.RootError:
            raise tmt.utils.SpecificationError(
                f"Repository '{self.url}' does not contain fmf metadata.")

    def __str__(self) -> str:
        """ Use repo/name for string representation """
        return f"{self.repo}{self.name}"

    @property
    def _library_cache(self) -> Dict[str, 'Library']:
        # Initialize library cache (indexed by the repository name)
        if not hasattr(self.parent, '_library_cache'):
            cast(CommonWithLibraryCache, self.parent)._library_cache = dict()

        return cast(CommonWithLibraryCache, self.parent)._library_cache

    def fetch(self) -> None:
        """ Fetch the library (unless already fetched) """
        # Check if the library was already fetched
        try:
            library = self._library_cache[self.repo]
            # The url must be identical
            if library.url != self.url:
                # tmt guessed url so try if repo exists
                if self.format == 'rpm':
                    with TemporaryDirectory() as tmp:
                        try:
                            tmt.utils.git_clone(str(self.url), str(tmp), self.parent,
                                                env={"GIT_ASKPASS": "echo"}, shallow=True)
                        except tmt.utils.RunError:
                            self.parent.debug(f"Repository '{self.url}' not found.")
                            raise LibraryError
                # If repo does exist we really have unsolvable url conflict
                raise tmt.utils.GeneralError(
                    f"Library '{self}' with url '{self.url}' conflicts "
                    f"with already fetched library from '{library.url}'.")
            # Use the default branch if no ref provided
            if self.ref is None:
                self.ref = library.default_branch
            # The same ref has to be used
            if library.ref != self.ref:
                raise tmt.utils.GeneralError(
                    f"Library '{self}' using ref '{self.ref}' conflicts "
                    f"with already fetched library '{library}' "
                    f"using ref '{library.ref}'.")
            self.parent.debug(f"Library '{self}' already fetched.", level=3)
            # Reuse the existing metadata tree
            self.tree: fmf.Tree = library.tree
        # Fetch the library and add it to the index
        except KeyError:
            self.parent.debug(f"Fetch library '{self}'.", level=3)
            # Prepare path, clone the repository, checkout ref
            assert self.parent.workdir
            directory = os.path.join(self.parent.workdir, self.dest, self.repo)
            # Clone repo with disabled prompt to ignore missing/private repos
            try:
                if self.url:
                    # Shallow clone to speed up testing and
                    # minimize data transfers if ref is not provided
                    tmt.utils.git_clone(self.url, directory, self.parent,
                                        env={"GIT_ASKPASS": "echo"}, shallow=self.ref is None)
                else:
                    # Either url or path must be defined
                    assert self.path is not None
                    self.parent.debug(
                        f"Copy local library '{self.path}' to '{directory}'.",
                        level=3)
                    shutil.copytree(self.path, directory, symlinks=True)
                # Detect the default branch from the origin
                try:
                    self.default_branch = tmt.utils.default_branch(directory)
                except OSError:
                    raise tmt.utils.GeneralError(
                        f"Unable to detect default branch for '{directory}'. "
                        f"Is the git repository '{self.url}' empty?")
                # Use the default branch if no ref provided
                if self.ref is None:
                    self.ref = self.default_branch
            except tmt.utils.RunError:
                # Fallback to install during the prepare step if in rpm format
                if self.format == 'rpm':
                    self.parent.debug(f"Repository '{self.url}' not found.")
                    raise LibraryError
                self.parent.fail(
                    f"Failed to fetch library '{self}' from '{self.url}'.")
                raise
            # Check out the requested branch
            try:
                self.parent.run(
                    ['git', 'checkout', self.ref], cwd=directory)
            except tmt.utils.RunError:
                # Fallback to install during the prepare step if in rpm format
                if self.format == 'rpm':
                    self.parent.debug(f"Invalid reference '{self.ref}'.")
                    raise LibraryError
                self.parent.fail(
                    f"Reference '{self.ref}' for library '{self}' not found.")
                raise
            # Initialize metadata tree, add self into the library index
            self.tree = fmf.Tree(directory)
            self._library_cache[self.repo] = self

        # Get the library node, check require and recommend
        library_node = self.tree.find(self.name)
        if not library_node:
            # Fallback to install during the prepare step if in rpm format
            if self.format == 'rpm':
                self.parent.debug(
                    f"Library '{self.name.lstrip('/')}' not found "
                    f"in the '{self.url}' repo.")
                raise LibraryError
            raise tmt.utils.GeneralError(
                f"Library '{self.name}' not found in '{self.repo}'.")
        self.require = cast(List[str], tmt.utils.listify(library_node.get('require', [])))
        self.recommend = cast(List[str], tmt.utils.listify(library_node.get('recommend', [])))

        # Create a symlink if the library is deep in the structure
        # FIXME: hot fix for https://github.com/beakerlib/beakerlib/pull/72
        # Covers also cases when library is stored more than 2 levels deep
        if os.path.dirname(self.name).lstrip('/'):
            link = self.name.lstrip('/')
            path = os.path.join(self.tree.root, os.path.basename(self.name))
            self.parent.debug(
                f"Create a '{link}' symlink as the library is stored "
                f"deep in the directory structure.")
            try:
                os.symlink(link, path)
            except OSError as error:
                self.parent.warn(
                    f"Unable to create a '{link}' symlink "
                    f"for a deep library ({error}).")


def dependencies(
    original_require: List[str],
    original_recommend: Optional[List[str]] = None,
    parent: Optional[tmt.utils.Common] = None,
    imported_lib_ids: ImportedIdentifiersType = None,
        ) -> LibraryDependenciesType:
    """
    Check dependencies for possible beakerlib libraries

    Fetch all identified libraries, check their required and recommended
    packages. Return tuple (requires, recommends, libraries) containing
    list of regular rpm package names aggregated from all fetched
    libraries, list of aggregated recommended packages and a list of
    gathered libraries (instances of the Library class).

    Avoid infinite recursion by keeping track of imported library identifiers
    and not trying to fetch those again.
    """
    # Initialize lists, use set for require & recommend
    processed_require = set()
    processed_recommend = set()
    imported_lib_ids = imported_lib_ids or []
    gathered_libraries = []
    original_require = original_require or []
    original_recommend = original_recommend or []

    # Cut circular dependencies to avoid infinite recursion
    def already_fetched(lib: str) -> bool:
        if not imported_lib_ids:
            return True
        return lib not in imported_lib_ids

    to_fetch = original_require + original_recommend
    for dependency in filter(already_fetched, to_fetch):
        # Library require/recommend
        try:
            library = Library(dependency, parent=parent)
            gathered_libraries.append(library)
            imported_lib_ids.append(library.identifier)
            # Recursively check for possible dependent libraries
            requires, recommends, libraries = dependencies(
                library.require, library.recommend, parent, imported_lib_ids)
            processed_require.update(set(requires))
            processed_recommend.update(set(recommends))
            gathered_libraries.extend(libraries)
        # Regular package require/recommend
        except LibraryError:
            if dependency in original_require:
                processed_require.add(dependency)
            if dependency in original_recommend:
                processed_recommend.add(dependency)

    # Convert to list and return the results
    return list(processed_require), list(processed_recommend), gathered_libraries
