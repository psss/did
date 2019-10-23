# coding: utf-8

""" Base Metadata Classes """

import os
import re
import fmf
import pprint

import tmt.steps
import tmt.templates

import tmt.steps.discover
import tmt.steps.provision
import tmt.steps.prepare
import tmt.steps.execute
import tmt.steps.report
import tmt.steps.finish

from tmt.utils import verdict
from click import echo, style

# Default workdir root
WORKDIR_ROOT = '/var/tmp/tmt'


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
    def overview(tree):
        """ Show overview of available tests """
        tests = [
            style(str(test), fg='red') for test in tree.tests()]
        echo(style(
            'Found {}{}{}.'.format(
                fmf.utils.listed(tests, 'test'),
                ': ' if tests else '',
                fmf.utils.listed(tests, max=12)
            ), fg='blue'))

    @staticmethod
    def create(name, template, tree, force=False):
        """ Create a new test """
        # Create directory
        directory_path = os.path.join(tree.root, name.lstrip('/'))
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

    def __init__(self, node, run=None):
        """ Initialize the plan """
        super(Plan, self).__init__(node)
        self.summary = node.get('summary')
        self.run = run
        self._workdir = None

        # Initialize test steps
        self.discover = tmt.steps.discover.Discover(
            self.node.get('discover'), self)
        self.provision = tmt.steps.provision.Provision(
            self.node.get('provision'), self)
        self.prepare = tmt.steps.prepare.Prepare(
            self.node.get('prepare'), self)
        self.execute = tmt.steps.execute.Execute(
            self.node.get('execute'), self)
        self.report = tmt.steps.report.Report(
            self.node.get('report'), self)
        self.finish = tmt.steps.finish.Finish(
            self.node.get('finish'), self)

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
    def overview(tree):
        """ Show overview of available plans """
        plans = [
            style(str(plan), fg='red') for plan in tree.plans()]
        echo(style(
            'Found {}{}{}.'.format(
                fmf.utils.listed(plans, 'plan'),
                ': ' if plans else '',
                fmf.utils.listed(plans, max=12)
            ), fg='blue'))

    @staticmethod
    def create(name, template, tree, force=False):
        """ Create a new plan """
        # Prepare paths
        (directory, plan) = os.path.split(name)
        directory_path = os.path.join(tree.root, directory.lstrip('/'))
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

    @property
    def workdir(self):
        """ Get the workdir, create if does not exist """
        if self._workdir is None:
            self._workdir = os.path.join(
                self.run.workdir, self.name.lstrip('/'))
            tmt.utils.create_directory(self._workdir, 'workdir', quiet=True)
        return self._workdir

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
        'example',
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
    def create(name, template, tree, force=False):
        """ Create a new story """
        # Prepare paths
        (directory, story) = os.path.split(name)
        directory_path = os.path.join(tree.root, directory.lstrip('/'))
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
    def overview(tree):
        """ Show overview of available stories """
        stories = [
            style(str(story), fg='red') for story in tree.stories()]
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
                wrap = key != 'example'
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
            output += '\n{}\n{}\n'.format(title, '=~^:-><'[depth] * len(title))

        # Summary, story and description
        if self.summary and self.summary != self.node.parent.get('summary'):
            output += '\n{}\n'.format(self.summary)
        if self.story != self.node.parent.get('story'):
            output += '\n*{}*\n'.format(self.story.strip())
        if self.description:
            output += '\n{}\n'.format(self.description)

        # Examples
        if self.example:
            output += '\nExamples::\n\n'
            output += tmt.utils.format(
                '', self.example, wrap=False, indent=4,
                key_color=None, value_color=None) + '\n'

        # Status
        if not self.node.children:
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


class Run(object):
    """
    Test run

    Takes care of the work directory preparation.
    """

    def __init__(self, id_=None, tree=None):
        """ Initialize tree, workdir and plans """
        # Save the tree
        self.tree = tree if tree else tmt.Tree('.')
        # Prepare the workdir
        self.workdir = self._workdir(id_)
        # Initialize plans
        self.plans = [Plan(plan, run=self)
            for plan in self.tree.tree.prune(keys=['execute'])]

    def _workdir(self, id_):
        """
        Initialize the work directory

        Workdir under WORKDIR_ROOT is used/created if 'id' is provided.
        If 'id' is a path, that directory is used instead. Otherwise a
        new workdir is created under WORKDIR_ROOT.
        """
        # Construct the workdir
        if id_ is not None:
            # Use provided directory if path given
            if '/' in id_:
                workdir = id_
            # Construct directory name under workdir root
            else:
                if isinstance(id_, int):
                    id_ = str(id_).rjust(3, '0')
                directory = 'run-{}'.format(id_)
                workdir = os.path.join(WORKDIR_ROOT, directory)
        else:
            # Generate a unique run id
            for id_ in range(1, 1000):
                directory = 'run-{}'.format(str(id_).rjust(3, '0'))
                workdir = os.path.join(WORKDIR_ROOT, directory)
                if not os.path.exists(workdir):
                    break

        # Create the workdir
        echo("Using '{}' as the workdir.".format(workdir))
        tmt.utils.create_directory(workdir, 'workdir', quiet=True)
        return workdir

    def go(self):
        """ Go and do test steps for selected plans """
        echo(style('Found {0}.\n'.format(
            fmf.utils.listed(self.tree.plans(), 'plan')), fg='magenta'))
        for plan in self.plans:
            plan.ls(summary=True)
            plan.go()
            echo()
