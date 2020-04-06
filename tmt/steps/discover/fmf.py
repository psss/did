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

        # Make sure that filter is a list
        if 'filter' in self.data and not isinstance(self.data['filter'], list):
            self.data['filter'] = [self.data['filter']]

        # Process command line options, apply defaults
        for option in ['url', 'ref', 'path', 'test', 'filter']:
            value = self.opt(option)
            if value:
                self.data[option] = value

    def go(self):
        """ Discover available tests """
        super(DiscoverFmf, self).go()
        testdir = os.path.join(self.workdir, 'tests')

        # Clone provided git repository
        url = self.get('url')
        if url:
            self.info('url', url, 'green')
            self.debug(f"Clone '{url}' to '{testdir}'.")
            self.run(f'git clone {url} {testdir}')
        # Copy current directory to workdir
        else:
            directory = self.step.plan.run.tree.root
            self.info('directory', directory, 'green')
            self.debug("Copy '{}' to '{}'.".format(directory, testdir))
            shutil.copytree(directory, testdir)

        # Checkout revision if requested
        ref = self.get('ref')
        if ref:
            self.info('ref', ref, 'green')
            self.debug(f"Checkout ref '{ref}'.")
            self.run(f"git checkout -f {ref}", cwd=testdir)

        # Show filters if provided
        filters = self.get('filter', [])
        for filter_ in filters:
            self.info('filter', filter_, 'green')

        # Initialize the metadata tree, search for available tests
        self.debug(f"Check metadata tree in '{testdir}'.")
        if self.opt('dry'):
            return
        self._tests = tmt.Tree(testdir).tests(filters=filters)

        # Prefix test path with the 'tests' subdirectory
        for test in self._tests:
            test.path = f'/tests{test.path}'

    def tests(self):
        """ Return all discovered tests """
        return self._tests
