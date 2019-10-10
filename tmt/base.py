# coding: utf-8

""" Base Metadata Classes """

import os
import fmf
import pprint

import tmt.cli
import tmt.steps
import tmt.templates

from tmt.utils import verdict
from click import echo, style


class Node(object):
    """
    General node object

    Corresponds to given fmf.Tree node.
    Implements common Test, Plan and Story methods.
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

    def ls(self, summary=False):
        """ List node """
        echo(style(self.name, fg='red'))
        if summary and self.summary:
            tmt.utils.format('summary', self.summary)


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
        """ Initialize the test """
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


    @staticmethod
    def overview():
        """ Show overview of available tests """
        tests = [
            style(str(test), fg='red') for test in tmt.cli.tree.tests()]
        echo(style(
            'Found {}{}{}.'.format(
                fmf.utils.listed(tests, 'test'),
                ': ' if tests else '',
                fmf.utils.listed(tests, max=12)
            ), fg='blue'))

    @staticmethod
    def create(name, template, force):
        """ Create a new test """
        root = tmt.cli.tree.root

        # Create directory
        directory_path = os.path.join(root, name.lstrip('/'))
        if os.path.isdir(directory_path):
            echo("Directory '{}' already exists.".format(directory_path))
        else:
            try:
                os.makedirs(directory_path, exist_ok=True)
                echo("Directory '{}' created.".format(directory_path))
            except OSError as error:
                raise tmt.utils.GeneralError(
                    "Failed to create test directory '{}' ({})".format(
                        directory_path, error))

        # Create metadata
        metadata_path = os.path.join(directory_path, 'main.fmf')
        action = 'created'
        if os.path.exists(metadata_path):
            if force:
                action = 'overwritten'
            else:
                raise tmt.utils.GeneralError(
                    "File '{}' already exists.".format(metadata_path))
        try:
            with open(metadata_path, 'w') as metadata:
                metadata.write(tmt.templates.TEST_METADATA)
            echo("Metadata '{}' {}.".format(metadata_path, action))
        except OSError as error:
            raise tmt.utils.GeneralError(
                "Failed to create test metadata '{}' ({})".format(
                    metadata_path, error))

        # Create script
        script_path = os.path.join(directory_path, 'test.sh')
        action = 'created'
        if os.path.exists(script_path):
            if force:
                action = 'overwritten'
            else:
                raise tmt.utils.GeneralError(
                    "File '{}' already exists.".format(script_path))
        try:
            with open(script_path, 'w') as script:
                if template == 'shell':
                    script.write(tmt.templates.TEST_SHELL)
                if template == 'beakerlib':
                    script.write(tmt.templates.TEST_BEAKERLIB)
            os.chmod(script_path, 0o755)
            echo("Script '{}' {}.".format(script_path, action))
        except OSError as error:
            raise tmt.utils.GeneralError(
                "Failed to create test script '{}' ({})".format(
                    script_path, error))

    def show(self):
        """ Show test details """
        self.ls()
        for key in self._keys:
            value = getattr(self, key)
            if value is None:
                continue
            else:
                tmt.utils.format(key, value)


    def lint(self):
        """ Check test against the L1 metadata specification. """
        self.ls()
        echo(verdict(self.test is not None, 'test script must be defined'))
        echo(verdict(self.path is not None, 'directory path must be defined'))
        if self.summary is None:
            echo(verdict(2, 'summary is very useful for quick inspection'))
        elif len(self.summary) > 50:
            echo(verdict(2, 'summary should not exceed 50 characters'))


class Plan(Node):
    """ Plan object (L2 Metadata) """

    def __init__(self, node):
        """ Initialize the plan """
        super(Plan, self).__init__(node)
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

    @staticmethod
    def overview():
        """ Show overview of available plans """
        plans = [
            style(str(plan), fg='red') for plan in tmt.cli.tree.plans()]
        echo(style(
            'Found {}{}{}.'.format(
                fmf.utils.listed(plans, 'plan'),
                ': ' if plans else '',
                fmf.utils.listed(plans, max=12)
            ), fg='blue'))

    def show(self):
        """ Show plan details """
        self.ls(summary=True)
        for step in tmt.steps.STEPS:
            step = getattr(self, step)
            if step.data:
                tmt.utils.format(str(step), key_color='blue')
                step.show()

    def go(self):
        """ Execute the plan """
        self.discover.go()
        self.provision.go()
        self.prepare.go()
        self.execute.go()
        self.report.go()
        self.finish.go()


class Story(Node):
    """ User story object """

    # Supported attributes (listed in display order)
    _keys = [
        'summary',
        'story',
        'description',
        'examples',
        'implemented',
        'tested',
        'documented',
        ]

    def __init__(self, node):
        """ Initialize the story """
        super(Story, self).__init__(node)
        self.summary = node.get('summary')
        # Get all supported attributes
        for key in self._keys:
            setattr(self, key, self.node.get(key))

    def _match(
        self, implemented, tested, documented, covered,
        unimplemented, untested, undocumented, uncovered):
        """ Return true if story matches given conditions """
        if implemented and not self.implemented:
            return False
        if tested and not self.tested:
            return False
        if documented and not self.documented:
            return False
        if unimplemented and self.implemented:
            return False
        if untested and self.tested:
            return False
        if undocumented and self.documented:
            return False
        if uncovered and self.implemented and self.tested and self.documented:
            return False
        if covered and not (
                self.implemented and self.tested and self.documented):
            return False
        return True

    @staticmethod
    def overview():
        """ Show overview of available stories """
        stories = [
            style(str(story), fg='red') for story in tmt.cli.tree.stories()]
        echo(style(
            'Found {}{}{}.'.format(
                fmf.utils.listed(stories, 'story'),
                ': ' if stories else '',
                fmf.utils.listed(stories, max=12)
            ), fg='blue'))

    def show(self):
        """ Show story details """
        self.ls()
        for key in self._keys:
            value = getattr(self, key)
            if value is not None:
                # Do not wrap examples
                wrap = key != 'examples'
                tmt.utils.format(key, value, wrap=wrap)

    def coverage(self, code, test, docs):
        """ Show story coverage """
        if code:
            code = bool(self.implemented)
            echo(verdict(code, good='done', bad='todo') + ' ', nl=False)
        if test:
            test = bool(self.tested)
            echo(verdict(test, good='done', bad='todo') + ' ', nl=False)
        if docs:
            docs = bool(self.documented)
            echo(verdict(docs, good='done', bad='todo') + ' ', nl=False)
        echo(self)
        return (code, test, docs)


class Tree(object):
    """ Test Metadata Tree """

    def __init__(self, path='.'):
        """ Initialize path and tree """
        self._path = path
        self._tree = None

    @property
    def tree(self):
        """ Initialize tree only when accessed """
        if self._tree is None:
            try:
                self._tree = fmf.Tree(self._path)
            except fmf.utils.RootError:
                raise tmt.utils.GeneralError(
                    "No metadata found in the '{0}' directory.".format(
                        self._path))
        return self._tree

    @property
    def root(self):
        """ Metadata root """
        return self.tree.root

    def tests(self, keys=[], names=[], filters=[], conditions=[]):
        """ Search available tests """
        keys.append('test')
        return [Test(test) for test in self.tree.prune(
            keys=keys, names=names, filters=filters, conditions=conditions)]

    def plans(self, keys=[], names=[], filters=[], conditions=[]):
        """ Search available plans """
        keys.append('execute')
        return [Plan(plan) for plan in self.tree.prune(
            keys=keys, names=names, filters=filters, conditions=conditions)]

    def stories(self, keys=[], names=[], filters=[], conditions=[]):
        """ Search available stories """
        keys.append('story')
        return [Story(story) for story in self.tree.prune(
            keys=keys, names=names, filters=filters, conditions=conditions)]
