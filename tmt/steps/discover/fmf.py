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
        repository: https://github.com/psss/tmt
        revision: master
        destination: tmt
        filter: 'tier: 1'
"""

import os
import re
import fmf
import tmt
import shutil
import subprocess

from click import echo

class DiscoverFmf(object):
    """ Discover available tests from FMF metadata """

    def __init__(self, data, step):
        """ Check supported attributes """
        self.step = step
        # Test metadata tree details
        self.repository = data.get('repository')
        self.destination = data.get('destination')
        self.revision = data.get('revision')
        self.filter = data.get('filter')
        if self.filter and not isinstance(self.filter, list):
            self.filter = [self.filter]
        # Prepare the workdir path (based on destination)
        if self.repository:
            if not self.destination:
                self.destination = re.sub(r'^.*/', '', self.repository)
                self.destination = re.sub(r'\.git$', '', self.destination)
        elif not self.destination:
            self.destination = os.path.basename(self.step.plan.run.tree.root)
        self.workdir = os.path.join(self.step.workdir, self.destination)

    def clone(self):
        """ Prepare the repository """
        # Copy current repository to workdir
        if self.repository is None:
            directory = self.step.plan.run.tree.root
            echo("Copying '{}' to '{}'.".format(directory, self.workdir))
            shutil.copytree(directory, self.workdir)
        # Clone git repository
        else:
            echo("Cloning '{}' to '{}'.".format(self.repository, self.workdir))
            command = 'git clone {} {}'.format(self.repository, self.workdir)
            try:
                subprocess.check_call(command.split())
            except subprocess.CalledProcessError as error:
                raise tmt.utils.GeneralError(
                    "Failed to clone git repository '{}': {}".format(
                        self.repository, error))
        # Checkout revision if requested
        if self.revision:
            try:
                command = 'git checkout -f {}'.format(self.revision)
                subprocess.check_call(command.split(), cwd=self.workdir)
            except subprocess.CalledProcessError as error:
                raise tmt.utils.GeneralError(
                    "Failed to checkout revision '{}': {}".format(
                        self.revision, error))

    def go(self):
        """ Discover available tests """
        self.clone()
        self.tree = fmf.Tree(self.workdir)
        self.tests = [
            tmt.Test(test) for test in self.tree.prune(
                keys=['test'],
                filters=self.filter or [],
                names=tmt.base.Test._opt('names', []))]
