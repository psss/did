# coding: utf-8

""" Base Metadata Classes """

import os
import re
import fmf
import pprint
import subprocess

import tmt.steps
import tmt.utils
import tmt.export
import tmt.templates

import tmt.steps.discover
import tmt.steps.provision
import tmt.steps.prepare
import tmt.steps.execute
import tmt.steps.report
import tmt.steps.finish

from tmt.utils import verdict
from fmf.utils import listed
from click import echo, style

DEFAULT_TEST_DURATION = '5m'

class Node(tmt.utils.Common):
    """
    General node object

    Corresponds to given fmf.Tree node.
    Implements common Test, Plan and Story methods.
    """

    # Supported attributes
    _keys = ['name']

    def __init__(self, node, parent=None):
        """ Initialize the node """
        super(Node, self).__init__(parent=parent, name=node.name)
        self.node = node

    def __str__(self):
        """ Node name """
        return self.name

    def _sources(self):
        """ Show source files """
        echo(tmt.utils.format(
            'sources', self.node.sources, key_color='magenta'))

    def _check(self, key, expected, default=None):
        """ Check that key is of expected type, handle default """
        value = getattr(self, key)
        # Handle default
        if value is None:
            setattr(self, key, default)
            return
        # Check for correct type
        if not isinstance(value, expected):
            class_name = self.__class__.__name__.lower()
            raise tmt.utils.SpecificationError(
                f"Invalid '{key}' in {class_name} '{self.name}' (should be "
                f"a '{expected.__name__}', got a '{type(value).__name__}').")

    def _fmf_id(self):
        """ Show fmf identifier """
        echo(tmt.utils.format('fmf-id', self.fmf_id, key_color='magenta'))

    @property
    def fmf_id(self):
        """ Return full fmf identifier of the node """

        def run(command):
            """ Run command, return output """
            result = subprocess.run(command.split(), capture_output=True)
            return result.stdout.strip().decode("utf-8")

        fmf_id = {'name': self.name}

        # Prepare url (for now handle just the most common schemas)
        origin = run('git config --get remote.origin.url')
        fmf_id['url'] = tmt.utils.public_git_url(origin)

        # Get the ref (skip for master as it is the default)
        ref = run('git rev-parse --abbrev-ref HEAD')
        if ref != 'master':
            fmf_id['ref'] = ref

        # Construct path (if different from git root)
        git_root = run('git rev-parse --show-toplevel')
        fmf_root = self.node.root
        if git_root != fmf_root:
            fmf_id['path'] = os.path.join(
                '/', os.path.relpath(fmf_root, git_root))

        return fmf_id

    @classmethod
    def _save_context(cls, context):
        """ Save provided command line context for future use """
        super(Node, cls)._save_context(context)

        # Handle '.' as an alias for the current working directory
        names = cls._opt('names')
        if names is not None and '.' in names:
            root = context.obj.tree.root
            current = os.getcwd()
            # Handle special case when directly in the metadata root
            if current == root:
                path = '/'
            # Prepare path from the tree root to the current directory
            else:
                path = os.path.join('/', os.path.relpath(current, root))
            cls._context.params['names'] = (
                path if name == '.' else name for name in names)

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

    def export(self, format_='yaml', keys=None):
        """ Export data into requested format (yaml or dict) """
        if keys is None:
            keys = self._keys
        data = dict([(key, getattr(self, key)) for key in keys])
        # Choose proper format
        if format_ == 'dict':
            return data
        elif format_ == 'yaml':
            return tmt.utils.dict_to_yaml(data)
        else:
            raise tmt.utils.GeneralError(
                f"Invalid test export format '{format_}'.")


class Test(Node):
    """ Test object (L1 Metadata) """

    # Supported attributes (listed in display order)
    _keys = [
        # Basic test information
        'summary',
        'description',
        'contact',
        'component',

        # Test execution data
        'test',
        'path',
        'require',
        'environment',
        'duration',
        'enabled',
        'result',

        # Filtering attributes
        'tag',
        'tier',
        'relevancy',
        ]

    def __init__(self, data, name=None):
        """
        Initialize test data from an fmf node or a dictionary

        The following two methods are supported:

            Test(node)
            Test(dictionary, name)

        Test name is required when initializing from a dictionary.
        """

        # Create a simple test node if dictionary given
        if isinstance(data, dict):
            if name is None:
                raise tmt.utils.GeneralError(
                    'Name required to initialize test.')
            elif not name.startswith('/'):
                raise tmt.utils.SpecificationError(
                    "Test name should start with a '/'.")
            node = fmf.Tree(data)
            node.name = name
        else:
            node = data
        super().__init__(node)

        # Set all supported attributes
        for key in self._keys:
            setattr(self, key, self.node.get(key))

        # Path defaults to the node name
        self._check('path', expected=str, default=self.name)

        # Check that lists are lists and environment is a dictionary
        for key in ['component', 'require', 'tag']:
            self._check(key, expected=list, default=[])
        self._check('environment', expected=dict, default={})

        # Default duration, enabled and result
        self._check('duration', expected=str, default=DEFAULT_TEST_DURATION)
        self._check('enabled', expected=bool, default=True)
        self._check('result', expected=str, default='respect')

    @staticmethod
    def overview(tree):
        """ Show overview of available tests """
        tests = [
            style(str(test), fg='red') for test in tree.tests()]
        echo(style(
            'Found {}{}{}.'.format(
                listed(tests, 'test'),
                ': ' if tests else '',
                listed(tests, max=12)
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

    def show(self):
        """ Show test details """
        self.ls()
        for key in self._keys:
            value = getattr(self, key)
            if value not in [None, list(), dict()]:
                echo(tmt.utils.format(key, value))
        if self.opt('verbose'):
            self._sources()
            self._fmf_id()


    def lint(self):
        """ Check test against the L1 metadata specification. """
        self.ls()
        echo(verdict(self.test is not None, 'test script must be defined'))
        echo(verdict(self.path is not None, 'directory path must be defined'))
        if self.summary is None:
            echo(verdict(2, 'summary is very useful for quick inspection'))
        elif len(self.summary) > 50:
            echo(verdict(2, 'summary should not exceed 50 characters'))

    def export(
            self, format_='yaml', keys=None, environment=None, create=False):
        """
        Export test data into requested format

        In addition to 'yaml' and 'dict' it supports also a special
        format 'execute' used by the execute step which returns
        (test-name, test-data) tuples.
        """

        # Prepare special format for the executor
        if format_ == 'execute':
            name = self.name
            data = dict()
            data['test'] = self.test
            data['path'] = self.path
            if self.duration is not None:
                data['duration'] = self.duration
            # Combine environment variables (plan overrides test)
            if self.environment or environment:
                combined_environment = dict()
                if self.environment:
                    combined_environment.update(self.environment)
                if environment:
                    combined_environment.update(environment)
                data['environment'] = ' '.join(
                    tmt.utils.shell_variables(self.environment))
            return name, data

        # Export to Nitrate test case management system
        elif format_ == 'nitrate':
            tmt.export.export_to_nitrate(self, create)

        # Common node export otherwise
        else:
            return super(Test, self).export(format_, keys)


class Plan(Node):
    """ Plan object (L2 Metadata) """

    def __init__(self, node, run=None):
        """ Initialize the plan """
        super(Plan, self).__init__(node, parent=run)
        self.summary = node.get('summary')
        self.run = run

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

        # Environment variables
        self.environment = node.get('environment')

    @staticmethod
    def overview(tree):
        """ Show overview of available plans """
        plans = [
            style(str(plan), fg='red') for plan in tree.plans()]
        echo(style(
            'Found {}{}{}.'.format(
                listed(plans, 'plan'),
                ': ' if plans else '',
                listed(plans, max=12)
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

    def steps(self, enabled=True, disabled=False, names=False, skip=[]):
        """
        Iterate over enabled / all steps

        Yields instances of all enabled steps by default. Use 'names' to
        yield step names only and 'disabled=True' to iterate over all.
        Use 'skip' to pass the list of steps to be skipped.
        """
        for name in tmt.steps.STEPS:
            if name in skip:
                continue
            step = getattr(self, name)
            if (enabled and step.enabled or disabled and not step.enabled):
                yield name if names else step

    def show(self):
        """ Show plan details """
        self.ls(summary=True)
        for step in self.steps(disabled=True):
            step.show()
        if self.environment is not None:
            echo(tmt.utils.format(
                'environment', self.environment, key_color='blue'))
        if self.opt('verbose'):
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
        # Show plan name and summary (one blank line to separate plans)
        self.info('')
        self.info(self.name, color='red')
        if self.summary:
            self.verbose('summary', self.summary, 'green')
        # Wake up all steps
        self.debug('wake', color='cyan', shift=0)
        for step in self.steps(disabled=True):
            self.debug(str(step), color='blue')
            step.wake()
        # Run enabled steps except 'finish'
        self.debug('go', color='cyan', shift=0)
        try:
            for step in self.steps(skip=['finish']):
                step.go()
        # Make sure we run 'finish' step always if enabled
        finally:
            if self.finish.enabled:
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
                listed(stories, 'story'),
                ': ' if stories else '',
                listed(stories, max=12)
            ), fg='blue'))

    def show(self):
        """ Show story details """
        self.ls()
        for key in self._keys:
            value = getattr(self, key)
            if value is not None:
                wrap = False if key == 'example' else 'auto'
                echo(tmt.utils.format(key, value, wrap=wrap))
        if self.opt('verbose'):
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
                listed(status) if status else 'idea')

        return output


class Tree(tmt.utils.Common):
    """ Test Metadata Tree """

    def __init__(self, path='.', tree=None):
        """ Initialize tmt tree from directory path or given fmf tree """
        self._path = path
        self._tree = tree

    @property
    def tree(self):
        """ Initialize tree only when accessed """
        if self._tree is None:
            try:
                self._tree = fmf.Tree(self._path)
            except fmf.utils.RootError:
                raise tmt.utils.GeneralError(
                    f"No metadata found in the '{self._path}' directory. "
                    f"Use 'tmt init' to get started.")
            except fmf.utils.FileError as error:
                raise tmt.utils.GeneralError(f"Invalid yaml syntax: {error}")
        return self._tree

    @property
    def root(self):
        """ Metadata root """
        return self.tree.root

    def tests(self, keys=[], names=[], filters=[], conditions=[]):
        """ Search available tests """
        # Apply possible command line options
        if Test._opt('names'):
            names.extend(Test._opt('names'))
        if Test._opt('filters'):
            filters.extend(Test._opt('filters'))
        if Test._opt('conditions'):
            conditions.extend(Test._opt('conditions'))
        # Build the list and convert to objects
        keys.append('test')
        return [Test(test) for test in self.tree.prune(
            keys=keys, names=names, filters=filters, conditions=conditions)]

    def plans(self, keys=[], names=[], filters=[], conditions=[], run=None):
        """ Search available plans """
        # Apply possible command line options
        if Plan._opt('names'):
            names.extend(Plan._opt('names'))
        if Plan._opt('filters'):
            filters.extend(Plan._opt('filters'))
        if Plan._opt('conditions'):
            conditions.extend(Plan._opt('conditions'))
        # Build the list and convert to objects
        keys.append('execute')
        return [Plan(plan, run=run) for plan in self.tree.prune(
            keys=keys, names=names, filters=filters, conditions=conditions)]

    def stories(
            self, keys=[], names=[], filters=[], conditions=[], whole=False):
        """ Search available stories """
        # Apply possible command line options
        if Story._opt('names'):
            names.extend(Story._opt('names'))
        if Story._opt('filters'):
            filters.extend(Story._opt('filters'))
        if Story._opt('conditions'):
            conditions.extend(Story._opt('conditions'))
        # Build the list and convert to objects
        keys.append('story')
        return [Story(story) for story in self.tree.prune(
            keys=keys, names=names,
            filters=filters, conditions=conditions, whole=whole)]


class Run(tmt.utils.Common):
    """ Test run, a container of plans """

    def __init__(self, id_=None, tree=None):
        """ Initialize tree, workdir and plans """
        super(Run, self).__init__()
        # Save the tree
        self.tree = tree if tree else tmt.Tree('.')
        # Prepare the workdir
        self._workdir_init(id_)
        self.debug(f"Using tree '{self.tree.root}'.")
        self._plans = None

    def save(self):
        """ Save list of selected plans and enabled steps """
        data = dict(
            plans = [plan.name for plan in self._plans],
            steps = list(self._context.obj.steps),
            )
        self.write('run.yaml', tmt.utils.dict_to_yaml(data))

    def load(self):
        """ Load list of selected plans and enabled steps """
        try:
            data = tmt.utils.yaml_to_dict(self.read('run.yaml'))
        except tmt.utils.FileError:
            self.debug('Run data not found.')
            return

        # Filter plans by name unless specified on the command line
        plan_options = ['names', 'filters', 'conditions']
        if not any([Plan._opt(option) for option in plan_options]):
            self._plans = [
                plan for plan in self.tree.plans(run=self)
                if plan.name in data['plans']]

        # Initialize steps only if not specified on the command line
        if not self.opt('all_') and not self._context.obj.steps:
            self._context.obj.steps = set(data['steps'])

    @property
    def plans(self):
        """ Test plans for execution """
        if self._plans is None:
            self._plans = self.tree.plans(run=self)
        return self._plans

    def go(self):
        """ Go and do test steps for selected plans """
        # Show run id / workdir path
        self.info(self.workdir, color='magenta')
        # Attempt to load run data
        self.load()
        # Enable all steps if none selected or --all provided
        if self.opt('all_') or not self._context.obj.steps:
            self._context.obj.steps = set(tmt.steps.STEPS)
        # Show summary, store run data
        self.verbose('Found {0}.'.format(listed(self.plans, 'plan')))
        self.save()
        # Iterate over plans
        for plan in self.plans:
            plan.go()
