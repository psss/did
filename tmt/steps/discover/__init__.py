# coding: utf-8

""" Discover Step Classes """

import tmt


class Discover(tmt.steps.Step):
    """ Gather and show information about test cases to be executed """
    name = 'discover'

    def show(self):
        """ Show discover details """
        super(Discover, self).show(
            keys=['how', 'filter', 'repository', 'tests'])
