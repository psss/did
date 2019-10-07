# coding: utf-8

""" Base Metadata Classes """

from __future__ import unicode_literals, absolute_import
from click import echo, style

import fmf
import pprint

import tmt.steps


class Node(object):
    """
    General node object

    Corresponds to given fmf.Tree node.
    Implements common Test, Testset and Story methods.
    """

    def __init__(self, node):
        """ Initialize the node """
        self.node = node
        self.name = node.name
        self.summary = node.get('summary')

    def __str__(self):
        """ Node name """
        return self.name

    def name_and_summary(self):
        """ Node name and optional summary """
        if self.summary:
            return '{0} ({1})'.format(self.name, self.summary)
        else:
            return self.name

    def ls(self):
        """ List node """
        echo(style(self.name, fg='red'))

    def show(self):
        """ Show node details """
        echo(style('{}: {}'.format(self.__class__.__name__, self), fg='green'))
        if self.summary:
            echo(style('Summary: {}'.format(self.summary), fg='green'))


class Test(Node):
    """ Test object (L1 Metadata) """

    def __init__(self, node):
        """ Initialize test """
        super(Test, self).__init__(node)


class Testset(Node):
    """ Testset object (L2 Metadata) """

    def __init__(self, node):
        """ Initialize testset steps """
        super(Testset, self).__init__(node)

        # Initialize test steps
        self.discover = tmt.steps.Discover(self.node.get('discover'))
        self.provision = tmt.steps.Provision(self.node.get('provision'))
        self.prepare = tmt.steps.Prepare(self.node.get('prepare'))
        self.execute = tmt.steps.Execute(self.node.get('execute'))
        self.report = tmt.steps.Report(self.node.get('report'))
        self.finish = tmt.steps.Finish(self.node.get('finish'))

        # Relevant artifacts & gates (convert to list if needed)
        self.artifacts = node.get('artifacts')
        if self.artifacts:
            if not isinstance(artifacts, list):
                artifacts = [artifacts]
        self.gates = node.get('gates')
        if self.gates:
            if not isinstance(gates, list):
                gates = [gates]

    def go(self):
        """ Execute the testset """
        self.discover.go()
        self.provision.go()
        self.prepare.go()
        self.execute.go()
        self.report.go()
        self.finish.go()


class Story(Node):
    """ User story object """

    def __init__(self, node):
        """ Initialize test """
        super(Story, self).__init__(node)


class Tree(object):
    """ Test Metadata Tree """

    def __init__(self, path='.'):
        """ Initialize testsets for given directory path """
        self.tree = fmf.Tree(path)

    def tests(self, keys=[], names=[], filters=[], conditions=[]):
        """ Search available tests """
        keys.append('test')
        return [Test(test) for test in self.tree.prune(
            keys=keys, names=names, filters=filters, conditions=conditions)]

    def testsets(self, keys=[], names=[], filters=[], conditions=[]):
        """ Search available testsets """
        keys.append('execute')
        return [Testset(testset) for testset in self.tree.prune(
            keys=keys, names=names, filters=filters, conditions=conditions)]

    def stories(self, keys=[], names=[], filters=[], conditions=[]):
        """ Search available stories """
        keys.append('story')
        return [Story(story) for story in self.tree.prune(
            keys=keys, names=names, filters=filters, conditions=conditions)]
