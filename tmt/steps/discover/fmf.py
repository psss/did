# coding: utf-8

"""
FMF Tests Discovery

Minimal config example (all available tests from the current
repository used by default)::

    discover:
        how: fmf

Full config example::

    discover:
        how: fmf
        url: https://github.com/psss/tmt
        ref: master
        path: /fmf/root
        test: /tests/basic
        filter: 'tier: 1'
"""

import os
import fmf
import tmt
import shutil
import click
import tmt.steps.discover

class DiscoverFmf(tmt.steps.discover.DiscoverPlugin):
    """ Discover available tests from fmf metadata """

    # Supported methods
    _methods = [
        tmt.steps.Method(
            name='fmf',
            summary='Flexible Metadata Format',
            order=50),
        ]

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
            self.run(f'git clone {url} {testdir}')
        # Copy git repository root to workdir
        else:
            if path and not os.path.isdir(path):
                raise tmt.utils.GeneralError(
                    f"Provided path '{path}' is not a directory.")
            fmf_root = path or self.step.plan.run.tree.root
            output = self.run('git rev-parse --show-toplevel', cwd=fmf_root)
            git_root = output[0].strip('\n')
            # Set path to relative path from the git root to fmf root
            path = os.path.relpath(fmf_root, git_root)
            self.info('directory', git_root, 'green')
            self.debug(f"Copy '{git_root}' to '{testdir}'.")
            shutil.copytree(git_root, testdir)

        # Checkout revision if requested
        ref = self.get('ref')
        if ref:
            self.info('ref', ref, 'green')
            self.debug(f"Checkout ref '{ref}'.")
            self.run(f"git checkout -f {ref}", cwd=testdir)

        # Adjust path and optionally show
        if path is None or path == '.':
            path = ''
        else:
            self.info('path', path, 'green')

        # Prepare the whole tree path and test path prefix
        tree_path = os.path.join(testdir, path.lstrip('/'))
        if not os.path.isdir(tree_path):
            raise tmt.utils.GeneralError(
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
            return
        self._tests = tmt.Tree(tree_path).tests(filters=filters, names=names)

        # Prefix test path with 'tests' and possible 'path' prefix
        for test in self._tests:
            test.path = os.path.join(prefix_path, test.path.lstrip('/'))

    def tests(self):
        """ Return all discovered tests """
        return self._tests
