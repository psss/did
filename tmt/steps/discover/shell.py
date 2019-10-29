# coding: utf-8

""" Shell Tests Discovery """

import tmt
import shutil
import tmt.steps.discover

class DiscoverShell(tmt.steps.discover.DiscoverPlugin):
    """ Discover available tests from manually provided list """

    def __init__(self, data, step):
        """ Check supported attributes """
        super(DiscoverShell, self).__init__(
            data=data, step=step, name=data['name'])

    def go(self):
        """ Discover available tests """

    def tests(self):
        return []
