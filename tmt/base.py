# coding: utf-8

""" Base Metadata Classes """

import os
import re
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

    def _sources(self):
        """ Show source files """
        echo(tmt.utils.format(
            'sources', self.node.sources, key_color='magenta'))

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
            echo(tmt.utils.format('summary', self.summary))


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
    def create(name, template, force=False):
        """ Create a new test """
        # Create directory
        directory_path = os.path.join(tmt.cli.tree.root, name.lstrip('/'))
        tmt.utils.create_directory(directory_path, 'test directory')

        # Create metadata
        metadata_path = os.path.join(directory_path, 'main.fmf')
        tmt.utils.create_file(
            path=metadata_path, content=tmt.templates.TEST_METADATA,
            name='test metadata', force=force)

        # Create script
        script_path = os.path.join(directory_path, 'test.sh')
        try:
            content = tmt.templates.TEST[template]
        except KeyError:
            raise tmt.utils.GeneralError(
                "Invalid template '{}'.".format(template))
        tmt.utils.create_file(
            path=script_path, content=content,
            name='test script', force=force, mode=0o755)

    def show(self, verbose):
        """ Show test details """
        self.ls()
        for key in self._keys:
            value = getattr(self, key)
            if value is None:
                continue
            else:
                echo(tmt.utils.format(key, value))
        if verbose:
            self._sources()

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

    @staticmethod
    def create(name, template, force=False):
        """ Create a new plan """
        # Prepare paths
        (directory, plan) = os.path.split(name)
        directory_path = os.path.join(tmt.cli.tree.root, directory.lstrip('/'))
        plan_path = os.path.join(directory_path, plan + '.fmf')

        # Create directory & plan
        tmt.utils.create_directory(directory_path, 'plan directory')
        try:
            content = tmt.templates.PLAN[template]
        except KeyError:
            raise tmt.utils.GeneralError(
                "Invalid template '{}'.".format(template))
        tmt.utils.create_file(
            path=plan_path, content=content,
            name='plan', force=force)

    def show(self, verbose):
        """ Show plan details """
        self.ls(summary=True)
        for step in tmt.steps.STEPS:
            step = getattr(self, step)
            if step.data:
                step.show()
        if verbose:
            self._sources()

    def lint(self):
        """ Check plan against the L2 metadata specification. """
        self.ls()
        execute = self.node.get('execute')
        echo(verdict(execute is not None, 'execute step must be defined'))
        if self.summary is None:
            echo(verdict(2, 'summary is very useful for quick inspection'))
        elif len(self.summary) > 50:
            echo(verdict(2, 'summary should not exceed 50 characters'))

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
    def create(name, template, force=False):
        """ Create a new story """
        # Prepare paths
        (directory, story) = os.path.split(name)
        directory_path = os.path.join(tmt.cli.tree.root, directory.lstrip('/'))
        story_path = os.path.join(directory_path, story + '.fmf')

        # Create directory & story
        tmt.utils.create_directory(directory_path, 'story directory')
        try:
            content = tmt.templates.STORY[template]
        except KeyError:
            raise tmt.utils.GeneralError(
                "Invalid template '{}'.".format(template))
        tmt.utils.create_file(
            path=story_path, content=content,
            name='story', force=force)

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

    def show(self, verbose):
        """ Show story details """
        self.ls()
        for key in self._keys:
            value = getattr(self, key)
            if value is not None:
                # Do not wrap examples
                wrap = key != 'examples'
                echo(tmt.utils.format(key, value, wrap=wrap))
        if verbose:
            self._sources()

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

    def export(self, format_='rst', title=True):
        """ Export story data into requested format """

        output = ''

        # Title
        if title:
            depth = len(re.findall('/', self.name)) - 1
            title = re.sub('.*/', '', self.name)
            output += '\n{}\n{}\n'.format(title, '=~^:-'[depth] * len(title))

        # Summary, story and description
        if self.summary and self.summary != self.node.parent.get('summary'):
            output += '\n{}\n'.format(self.summary)
        if self.story != self.node.parent.get('story'):
            output += '\n*{}*\n'.format(self.story.strip())
        if self.description:
            output += '\n{}\n'.format(self.description)

        # Examples
        if self.examples:
            output += '\nExamples::\n\n'
            output += tmt.utils.format(
                '', self.examples, wrap=False, indent=4,
                key_color=None, value_color=None) + '\n'

        # Status
        if self.node.children:
            return output
        status = []
        for coverage in ['implemented', 'tested', 'documented']:
            if getattr(self, coverage):
                status.append(coverage)
        output += "\nStatus: {}\n".format(
            fmf.utils.listed(status) if status else 'idea')

        return output


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

    def stories(
            self, keys=[], names=[], filters=[], conditions=[], whole=False):
        """ Search available stories """
        keys.append('story')
        return [Story(story) for story in self.tree.prune(
            keys=keys, names=names,
            filters=filters, conditions=conditions, whole=whole)]
