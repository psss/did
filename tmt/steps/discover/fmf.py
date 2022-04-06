import os
import re
import shutil
import subprocess

import click
import fmf

import tmt
import tmt.beakerlib
import tmt.steps.discover
from tmt.utils import MetadataError


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
            url: https://github.com/teemtee/tmt
            ref: main
            path: /fmf/root
            test: /tests/basic
            filter: 'tier: 1'

    If no 'ref' is provided, the default branch from the origin is used.

    For DistGit repo one can extract source tarball first and discover
    tests from it by using 'distgit-source: true'. It can be used
    together with 'ref', 'path' and 'url'.

        discover:
            how: fmf
            dist-git-source: true

    Selecting tests containting specified link is possible using 'link'
    option accepting RELATION:TARGET format of values. Regular
    expressions are supported for both relation and target part of the
    value. Relation can be omitted to target match any relation.

        discover:
            how: fmf
            link: verifies:.*issue/850$

    It is also possible to limit tests only to those that have changed
    in git since a given revision. This can be particularly useful when
    testing changes to tests themselves (e.g. in a pull request CI).

    Related config options (all optional):
    * modified-only - set to True if you want to filter modified tests
    * modified-url - fetched as "reference" remote in the test dir
    * modified-ref - the ref to compare against

    Example to compare local repo against upstream 'main' branch:

        discover:
            how: fmf
            modified-only: True
            modified-url: https://github.com/teemtee/tmt
            modified-ref: reference/main

    Note that internally the modified tests are appended to the list
    specified via 'test', so those tests will also be selected even if
    not modified.
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='fmf', doc=__doc__, order=50)]

    # Supported keys
    _keys = [
        "url", "ref", "path", "test", "link", "filter",
        "modified-only", "modified-url", "modified-ref",
        "dist-git-source", "dist-git-type", "fmf-id", "exclude"]

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
                '--modified-url', metavar='REPOSITORY',
                help='URL of the reference git repository with fmf metadata.'),
            click.option(
                '--modified-ref', metavar='REVISION',
                help='Branch, tag or commit specifying the reference git '
                'revision (if not provided, the default branch is used).'),
            click.option(
                '-m', '--modified-only', is_flag=True,
                help='If set, select only tests modified '
                'since reference revision.'),
            click.option(
                '-p', '--path', metavar='ROOT',
                help='Path to the metadata tree root.'),
            click.option(
                '-t', '--test', metavar='NAMES', multiple=True,
                help='Select tests by name.'),
            click.option(
                '--link', metavar="RELATION:TARGET", multiple=True,
                help="Filter by linked objects (regular expressions are "
                     "supported for both relation and target)."),
            click.option(
                '-F', '--filter', metavar='FILTERS', multiple=True,
                help='Include only tests matching the filter.'),
            click.option(
                '--dist-git-source', is_flag=True,
                help='Extract DistGit sources and run discover on top of it.'),
            click.option(
                '--dist-git-type',
                type=click.Choice(tmt.utils.get_distgit_handler_names()),
                help='Use the provided DistGit handler instead of detection.'),
            click.option(
                '-x', '--exclude', metavar='[REGEXP]', multiple=True,
                help="Exclude a regular expression from search result."),
            click.option(
                '--fmf-id', default=False, is_flag=True,
                help='Show fmf identifiers for tests discovered in plan.')
            ] + super().options(how)

    def wake(self, keys=None):
        """ Wake up the plugin, process data, apply options """
        # Handle backward-compatible stuff
        if 'repository' in self.data:
            self.data['url'] = self.data.pop('repository')
        if 'revision' in self.data:
            self.data['ref'] = self.data.pop('revision')

        # Make sure that 'exclude', 'filter' and 'test' keys are lists
        tmt.utils.listify(self.data, keys=["exclude", "filter", "test"])

        # Process command line options, apply defaults
        super().wake(keys=keys)

    def go(self):
        """ Discover available tests """
        super(DiscoverFmf, self).go()

        # Check url and path, prepare test directory
        url = self.get('url')
        path = self.get('path')
        testdir = os.path.join(self.workdir, 'tests')
        dist_git_source = self.get('dist-git-source', False)

        # Raise an exception if --fmf-id uses w/o url and git root
        # doesn't exist for discovered plan
        if self.opt('fmf_id'):
            def assert_git_url(plan_name=None):
                try:
                    subprocess.run(
                        'git rev-parse --show-toplevel'.split(),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        check=True)
                except subprocess.CalledProcessError:
                    raise tmt.utils.DiscoverError(
                        f"`tmt run discover --fmf-id` without `url` option in "
                        f"plan `{plan_name}` can be used only within"
                        f" git repo.")
            # It covers only one case, when there is:
            # 1) no --url on CLI
            # 2) plan w/o url exists in test run
            if not self.opt('url'):
                try:
                    fmf_tree = fmf.Tree(os.getcwd())
                except fmf.utils.RootError:
                    raise tmt.utils.DiscoverError(
                        f"No metadata found in the current directory. "
                        f"Use 'tmt init' to get started.")
                for i, attr in enumerate(fmf_tree.climb()):
                    try:
                        plan_url = attr.data.get('discover').get('url')
                        plan_name = attr.name
                        if not plan_url:
                            assert_git_url(plan_name)
                    except AttributeError:
                        pass
            # All other cases are covered by this condition
            if not url:
                assert_git_url(self.step.plan.name)

        # Clone provided git repository (if url given) with disabled
        # prompt to ignore possibly missing or private repositories
        if url:
            self.info('url', url, 'green')
            self.debug(f"Clone '{url}' to '{testdir}'.")
            self.run(
                ['git', 'clone', url, testdir],
                env={"GIT_ASKPASS": "echo"})
        # Copy git repository root to workdir
        else:
            # Path for distgit sources cannot be checked until the
            # tarball is extracted
            if path and not os.path.isdir(path) and not dist_git_source:
                raise tmt.utils.DiscoverError(
                    f"Provided path '{path}' is not a directory.")
            if dist_git_source:
                git_root = self.step.plan.my_run.tree.root
            else:
                fmf_root = path or self.step.plan.my_run.tree.root
                if fmf_root is None:
                    raise tmt.utils.DiscoverError(
                        f"No metadata found in the current directory.")
                # Check git repository root (use fmf root if not found)
                try:
                    output = self.run(
                        ["git", "rev-parse", "--show-toplevel"],
                        cwd=fmf_root, dry=True)
                    git_root = output[0].strip('\n')
                except tmt.utils.RunError:
                    self.debug(f"Git root not found, using '{fmf_root}.'")
                    git_root = fmf_root
                # Set path to relative path from the git root to fmf root
                path = os.path.relpath(fmf_root, git_root)
            self.info('directory', git_root, 'green')
            self.debug(f"Copy '{git_root}' to '{testdir}'.")
            if not self.opt('dry'):
                shutil.copytree(git_root, testdir, symlinks=True)

        # Checkout revision if requested
        ref = self.get('ref')
        if ref:
            self.info('ref', ref, 'green')
            self.debug(f"Checkout ref '{ref}'.")
            self.run(
                ['git', 'checkout', '-f', str(ref)],
                cwd=testdir)

        # Show current commit hash if inside a git repository
        try:
            hash_, _ = self.run(["git", "rev-parse", "--short", "HEAD"],
                                cwd=testdir)
            self.verbose('hash', hash_.strip(), 'green')
        except (tmt.utils.RunError, AttributeError):
            pass

        # Fetch and extract distgit sources
        if dist_git_source:
            try:
                self.extract_distgit_source(
                    testdir, testdir, self.get('dist-git-type'))
            except Exception as error:
                raise tmt.utils.DiscoverError(
                    f"Failed to process 'dist-git-source'.", original=error)

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
        # Check the 'test --filter' option first, then from discover
        filters = list(tmt.base.Test._opt('filters') or self.get('filter', []))
        for filter_ in filters:
            self.info('filter', filter_, 'green')
        # Names of tests selected by --test option
        names = self.get('test', [])
        if names:
            self.info('tests', fmf.utils.listed(names), 'green')
        # Check the 'test --link' option first, then from discover
        links = list(tmt.base.Test._opt('link') or self.get('link', []))
        for link_ in links:
            self.info('link', link_, 'green')

        excludes = list(tmt.base.Test._opt('exclude')
                        or self.get('exclude', []))

        # Filter only modified tests if requested
        modified_only = self.get('modified-only')
        modified_url = self.get('modified-url')
        if modified_url:
            self.info('modified-url', modified_url, 'green')
            self.debug(f"Fetch also '{modified_url}' as 'reference'.")
            self.run(['git', 'remote', 'add', 'reference', modified_url],
                     cwd=testdir)
            self.run(['git', 'fetch', 'reference'], cwd=testdir)
        if modified_only:
            modified_ref = self.get(
                'modified-ref', tmt.utils.default_branch(testdir))
            self.info('modified-ref', modified_ref, 'green')
            output = self.run(
                ['git', 'log', '--format=', '--stat', '--name-only',
                 f"{modified_ref}..HEAD"], cwd=testdir)[0]
            modified = set(
                f"^/{re.escape(name)}"
                for name in map(os.path.dirname, output.split('\n')) if name)
            self.debug(f"Limit to modified test dirs: {modified}", level=3)
            names.extend(modified)

        # Initialize the metadata tree, search for available tests
        self.debug(f"Check metadata tree in '{tree_path}'.")
        if self.opt('dry'):
            self._tests = []
            return
        tree = tmt.Tree(path=tree_path, context=self.step.plan._fmf_context())
        self._tests = tree.tests(
            filters=filters,
            names=names,
            conditions=["manual is False"],
            unique=False,
            links=links,
            excludes=excludes)

        # Prefix tests and handle library requires
        for test in self._tests:
            # Prefix test path with 'tests' and possible 'path' prefix
            test.path = os.path.join(prefix_path, test.path.lstrip('/'))
            # Check for possible required beakerlib libraries
            if test.require or test.recommend:
                test.require, test.recommend, _ = tmt.beakerlib.dependencies(
                    test.require, test.recommend, parent=self)

    def tests(self):
        """ Return all discovered tests """
        return self._tests
