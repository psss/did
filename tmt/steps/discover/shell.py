# coding: utf-8

""" Shell Tests Discovery """

import tmt
import shutil

class DiscoverShell(object):
    """ Discover available tests from FMF metadata """

    def __init__(self, data, parent):
        """ Check supported attributes """
        self.parent = parent
        self.repository = data.get('repository')
        self.destination = data.get('destination')
        self.filter = data.get('filter')
        self.tests = []

    def clone(self):
        """ Prepare the repository """
        # Copy current repository to workdir
        if self.repository is None:
            self.parent.plan.run.tree.root

    def go(self):
        """ Discover available tests """
