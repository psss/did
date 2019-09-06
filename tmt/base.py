# coding: utf-8

""" Base Metadata Classes """

from __future__ import unicode_literals, absolute_import

import fmf
import pprint

import tmt.steps


class Testset(object):
    """ Group of tests sharing the same test execution metadata """

    def __init__(self, node):
        """ Initialize testset steps """
        self.node = node
        self.name = node.name
        self.summary = node.get('summary')
        self.discover = tmt.steps.Discover(self.node.get('discover'))
        self.provision = tmt.steps.Provision(self.node.get('provision'))
        self.prepare = tmt.steps.Prepare(self.node.get('prepare'))
        self.execute = tmt.steps.Execute(self.node.get('execute'))
        self.report = tmt.steps.Report(self.node.get('report'))
        self.finish = tmt.steps.Finish(self.node.get('finish'))

    def __str__(self):
        """ Testset name and summary """
        if self.summary:
            return '{0} ({1})'.format(self.name, self.summary)
        else:
            return self.name

    def go(self):
        """ Execute the testset """
        self.discover.go()
        self.provision.go()
        self.prepare.go()
        self.execute.go()
        self.report.go()
        self.finish.go()


class Tree(object):
    """ Test Metadata Tree """

    def __init__(self, path='.'):
        """ Initialize testsets for given directory path """
        self.tree = fmf.Tree(path)
        self.testsets = [Testset(testset) for testset in self.tree.climb()]
