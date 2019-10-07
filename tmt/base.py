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


class Test(Node):
    """ Test object (L1 Metadata) """

    # Supported attributes (listed in display order)
    _keys = [
        'summary',
        'description',
        'contact',
        'component',
        'test',
        'path',
        'duration',
        'environment',
        'relevancy',
        'tags',
        'tier',
        'result',
        'enabled',
        ]

    def __init__(self, node):
        """ Initialize test """
        super(Test, self).__init__(node)
        # Get all supported attributes
        for key in self._keys:
            setattr(self, key, self.node.get(key))
        # Path defaults to the node name
        if self.path is None:
            self.path = self.name
        # Handle other default values
        if self.enabled is None:
            disabled = self.node.get('disabled')
            if disabled is not None:
                self.enabled = not disabled
            else:
                self.enabled = True
        if self.result is None:
            self.result = 'respect'

    def show(self):
        """ Show test details """
        self.ls()
        for key in self._keys:
            value = getattr(self, key)
            if value is None:
                continue
            else:
                tmt.utils.format(key, value)


class Testset(Node):
    """ Testset object (L2 Metadata) """

    def __init__(self, node):
        """ Initialize testset steps """
        super(Testset, self).__init__(node)
        self.summary = node.get('summary')

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

    def show(self):
        """ Show testset details """
        self.ls()
        if self.summary:
            tmt.utils.format('summary', self.summary)
        for step in tmt.steps.STEPS:
            step = getattr(self, step)
            if step.data:
                tmt.utils.format(str(step), key_color='blue')
                step.show()

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
        self.summary = node.get('summary')


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
