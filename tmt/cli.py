# coding: utf-8

""" Command line interface for the Test Management Tool """

from click import echo, style
from fmf.utils import listed

import click
import os

import fmf
import tmt
import tmt.utils
import tmt.plugins
import tmt.convert
import tmt.export
import tmt.steps
import tmt.templates
import tmt.options

# Explore available plugins (need to detect all supported methods first)
tmt.plugins.explore()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Custom Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CustomGroup(click.Group):
    """ Custom Click Group """

    def list_commands(self, context):
        """ Prevent alphabetical sorting """
        return self.commands.keys()

    def get_command(self, context, cmd_name):
        """ Allow command shortening """
        # Backward-compatible 'test convert' (just temporary for now FIXME)
        cmd_name = cmd_name.replace('convert', 'import')
        # Support both story & stories
        cmd_name = cmd_name.replace('story', 'stories')
        found = click.Group.get_command(self, context, cmd_name)
        if found is not None:
            return found
        matches = [command for command in self.list_commands(context)
                   if command.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, context, matches[0])
        context.fail('Did you mean {}?'.format(
            listed(sorted(matches), join='or')))

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Common Options
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def verbose_debug_quiet(function):
    """ Verbose, debug and quiet output """
    for option in reversed(tmt.options.verbose_debug_quiet):
        function = option(function)
    return function


def force_dry(function):
    """ Force and dry actions """
    for option in reversed(tmt.options.force_dry):
        function = option(function)
    return function


def name_filter_condition(function):
    """ Common filter option """
    options = [
        click.argument(
            'names', nargs=-1, metavar='[REGEXP]'),
        click.option(
            '--filter', 'filters', metavar='FILTER', multiple=True,
            help="Apply advanced filter (see 'pydoc fmf.filter')."),
        click.option(
            '--condition', 'conditions', metavar="EXPR", multiple=True,
            help="Use arbitrary Python expression for filtering."),
        ]

    for option in reversed(options):
        function = option(function)
    return function


def implemented_tested_documented(function):
    """ Common story options """

    options = [
        click.option(
            '-i', '--implemented', is_flag=True,
            help='Implemented stories only.'),
        click.option(
            '-I', '--unimplemented', is_flag=True,
            help='Unimplemented stories only.'),
        click.option(
            '-t', '--tested', is_flag=True,
            help='Tested stories only.'),
        click.option(
            '-T', '--untested', is_flag=True,
            help='Untested stories only.'),
        click.option(
            '-d', '--documented', is_flag=True,
            help='Documented stories only.'),
        click.option(
            '-D', '--undocumented', is_flag=True,
            help='Undocumented stories only.'),
        click.option(
            '-c', '--covered', is_flag=True,
            help='Covered stories only.'),
        click.option(
            '-C', '--uncovered', is_flag=True,
            help='Uncovered stories only.'),
        ]

    for option in reversed(options):
        function = option(function)
    return function


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@click.option(
    '-r', '--root', metavar='PATH', default='.', show_default=True,
    help='Path to the tree root.')
@verbose_debug_quiet
def main(context, root, **kwargs):
    """ Test Management Tool """
    # Initialize metadata tree
    tree = tmt.Tree(root)
    tree._save_context(context)
    context.obj = tmt.utils.Common()
    context.obj.tree = tree
    # List of enabled steps
    context.obj.steps = set()

    # Show overview of available tests, plans and stories
    if context.invoked_subcommand is None:
        tmt.Test.overview(tree)
        tmt.Plan.overview(tree)
        tmt.Story.overview(tree)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Run
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.group(chain=True, invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@click.option(
    '-i', '--id', 'id_', help='Run id (name or directory path).', metavar="ID")
@click.option(
    '-a', '--all', 'all_', help='Run all steps, customize some.', is_flag=True)
@click.option(
    '-e', '--environment', metavar='KEY=VALUE', multiple='True',
    help='Set environment variable. Can be specified multiple times.')
@verbose_debug_quiet
@force_dry
def run(context, all_, id_, environment, **kwargs):
    """ Run test steps. """
    # Initialize
    tmt.Run._save_context(context)
    run = tmt.Run(id_, context.obj.tree)
    context.obj.run = run

    # Check for sane environment variables
    for env in environment:
        if '=' not in env:
            raise tmt.utils.GeneralError(
                f"Invalid environment variable specification '{env}'.")


run.add_command(tmt.steps.discover.DiscoverPlugin.command())


@run.command()
@click.pass_context
@click.option(
    '-h', '--how', metavar='METHOD',
    help='Use specified method for provisioning.')
@click.option(
    '-i', '--image', metavar='IMAGE',
    help='Select image to use. Possible values depend on the method.')
@click.option(
    '-b', '--box', metavar='BOX',
    help='Vagrant box name to use.')
@click.option(
    '--vagrantfile', metavar='VAGRANTFILE',
    help='Vagrantfile to override initialized one and default entries.')
@click.option(
    '-m', '--memory', metavar='MEMORY',
    help='Set memory available to guest in MB.')
@click.option(
    '-u', '--user', metavar='USER',
    help='Username to use for all guest operations.')
@click.option(
    '-p', '--password', metavar='PASSWORD',
    help='Password to use for login into guest system.')
@click.option(
    '-k', '--key', metavar='PRIVATE_KEY',
    help='Private key to use for login into guest system.')
@click.option(
    '-g', '--guest', metavar='GUEST',
    help='Select remote host to connect to (how: connect).')
@click.option(
    '--container-pull', is_flag=True,
    help='Force pulling container image (how: container).')

@verbose_debug_quiet
@force_dry
def provision(context, **kwargs):
    """ Provision an environment for testing (or use localhost). """
    context.obj.steps.add('provision')
    tmt.steps.provision.Provision._save_context(context)


@run.command()
@click.pass_context
@click.option(
    '-h', '--how', metavar='METHOD',
    help='Use specified method for environment preparation.')
@click.option(
    '-s', '--script', metavar='SCRIPT',
    help='Scriplet or path or URI to a script to execute.')
@click.option(
    '-p', '--playbook', metavar='PLAYBOOK',
    help='Path or URI to ansible playbook to run.')
@verbose_debug_quiet
@force_dry
def prepare(context, **kwargs):
    """ Configure environment for testing (like ansible playbook). """
    context.obj.steps.add('prepare')
    tmt.steps.prepare.Prepare._save_context(context)


@run.command()
@click.pass_context
@click.option(
    '-h', '--how', metavar='METHOD',
    help='Use specified method for test execution.')
@click.option(
    '-s', '--script', metavar='SCRIPT', multiple=True,
    help='Shell script to be executed as a test.')
@verbose_debug_quiet
@force_dry
def execute(context, **kwargs):
    """ Run the tests (using the specified framework and its settings). """
    context.obj.steps.add('execute')
    tmt.steps.execute.Execute._save_context(context)


@run.command()
@click.pass_context
@click.option(
    '-h', '--how', metavar='METHOD',
    help='Use specified method for result reporting.')
@verbose_debug_quiet
@force_dry
def report(context, **kwargs):
    """ Provide an overview of test results and send notifications. """
    context.obj.steps.add('report')
    tmt.steps.report.Report._save_context(context)


@run.command()
@click.pass_context
@click.option(
    '-h', '--how', metavar='METHOD',
    help='Use specified method for finishing tasks.')
@verbose_debug_quiet
@force_dry
def finish(context, **kwargs):
    """ Additional actions to be performed after the test execution. """
    context.obj.steps.add('finish')
    tmt.steps.finish.Finish._save_context(context)


@run.command()
@click.pass_context
@click.option(
    '--name', 'names', metavar='REGEXP', multiple=True,
    help="Regular expression to match plan name.")
@click.option(
    '--filter', 'filters', metavar='FILTER', multiple=True,
    help="Apply advanced filter (see 'pydoc fmf.filter').")
@click.option(
    '--condition', 'conditions', metavar="EXPR", multiple=True,
    help="Use arbitrary Python expression for filtering.")
@verbose_debug_quiet
def plans(context, **kwargs):
    """
    Select plans which should be executed.

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.base.Plan._save_context(context)


@run.command()
@click.pass_context
@click.option(
    '--name', 'names', metavar='REGEXP', multiple=True,
    help="Regular expression to match test name.")
@click.option(
    '--filter', 'filters', metavar='FILTER', multiple=True,
    help="Apply advanced filter (see 'pydoc fmf.filter').")
@click.option(
    '--condition', 'conditions', metavar="EXPR", multiple=True,
    help="Use arbitrary Python expression for filtering.")
@verbose_debug_quiet
def tests(context, **kwargs):
    """
    Select tests which should be executed.

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.base.Test._save_context(context)


@run.resultcallback()
@click.pass_context
def finito(context, commands, *args, **kwargs):
    """ Run tests if run defined """
    if hasattr(context.obj, 'run'):
        context.obj.run.go()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Test
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@verbose_debug_quiet
def tests(context, **kwargs):
    """
    Manage tests (L1 metadata).

    Check available tests, inspect their metadata.
    Convert old metadata into the new fmf format.
    """

    # Show overview of available tests
    if context.invoked_subcommand is None:
        tmt.Test.overview(context.obj.tree)


@tests.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def ls(context, **kwargs):
    """
    List available tests

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    for test in context.obj.tree.tests():
        test.ls()


@tests.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def show(context, **kwargs):
    """
    Show test details

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    for test in context.obj.tree.tests():
        test.show()
        echo()


@tests.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def lint(context, **kwargs):
    """
    Check tests against the L1 metadata specification

    Regular expression can be used to filter tests for linting.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    for test in context.obj.tree.tests():
        test.lint()
        echo()


_test_templates = listed(tmt.templates.TEST, join='or')
@tests.command()
@click.pass_context
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    help='Test template ({}).'.format(_test_templates),
    prompt='Template ({})'.format(_test_templates))
@verbose_debug_quiet
@force_dry
def create(context, name, template, force, **kwargs):
    """ Create a new test based on given template. """
    tmt.Test._save_context(context)
    tmt.Test.create(name, template, context.obj.tree, force)


@tests.command(name='import')
@click.pass_context
@click.argument('paths', nargs=-1, metavar='[PATH]...')
@click.option(
    '--nitrate / --no-nitrate', default=True,
    help='Import test metadata from Nitrate')
@click.option(
    '--purpose / --no-purpose', default=True,
    help='Migrate description from PURPOSE file')
@click.option(
    '--makefile / --no-makefile', default=True,
    help='Convert Beaker Makefile metadata')
@click.option(
    '--disabled', default=False, is_flag=True,
    help='Import disabled test cases from Nitrate as well.')
@verbose_debug_quiet
@force_dry
def import_(context, paths, makefile, nitrate, purpose, disabled, **kwargs):
    """
    Import old test metadata into the new fmf format.

    Accepts one or more directories where old metadata are stored.
    By default all available sources and current directory are used.
    The following test metadata are converted for each source:

    \b
    makefile ..... summary, component, duration, require
    purpose ...... description
    nitrate ...... contact, component, tag,
                   environment, relevancy, enabled
    """
    tmt.Test._save_context(context)
    if not paths:
        paths = ['.']
    for path in paths:
        # Make sure we've got a real directory
        path = os.path.realpath(path)
        if not os.path.isdir(path):
            raise tmt.utils.GeneralError(
                "Path '{0}' is not a directory.".format(path))
        # Gather old metadata and store them as fmf
        common, individual = tmt.convert.read(
            path, makefile, nitrate, purpose, disabled)
        # Add path to common metadata if there are virtual test cases
        if individual:
            root = fmf.Tree(path).root
            common['path'] = os.path.join( '/', os.path.relpath(path, root))
        # Store common metadata
        common_path = os.path.join(path, 'main.fmf')
        tmt.convert.write(common_path, common)
        # Store individual data (as virtual tests)
        for testcase in individual:
            testcase_path = os.path.join(
                path, str(testcase['extra-nitrate']) + '.fmf')
            tmt.convert.write(testcase_path, testcase)


@tests.command()
@click.pass_context
@name_filter_condition
@click.option(
    '--nitrate', is_flag=True,
    help='Export test metadata to Nitrate.')
@click.option(
    '--create', is_flag=True,
    help="Create test cases in nitrate if they don't exist.")
@click.option(
    '--format', 'format_', default='yaml', show_default=True, metavar='FORMAT',
    help='Output format.')
@click.option(
    '-d', '--debug', is_flag=True,
    help='Provide as much debugging details as possible.')
def export(context, format_, nitrate, create, **kwargs):
    """
    Export test data into the desired format

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    for test in context.obj.tree.tests():
        if nitrate:
            test.export(format_='nitrate', create=create)
        else:
            echo(test.export(format_=format_))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Plan
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@verbose_debug_quiet
def plans(context, **kwargs):
    """
    Manage test plans (L2 metadata).

    \b
    Search for available plans.
    Explore detailed test step configuration.
    """
    tmt.Plan._save_context(context)

    # Show overview of available plans
    if context.invoked_subcommand is None:
        tmt.Plan.overview(context.obj.tree)


@plans.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def ls(context, **kwargs):
    """
    List available plans

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.Plan._save_context(context)
    for plan in context.obj.tree.plans():
        plan.ls()


@plans.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def show(context, **kwargs):
    """
    Show plan details

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.Plan._save_context(context)
    for plan in context.obj.tree.plans():
        plan.show()
        echo()


@plans.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def lint(context, **kwargs):
    """
    Check plans against the L2 metadata specification

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.Plan._save_context(context)
    for plan in context.obj.tree.plans():
        plan.lint()
        echo()


_plan_templates = listed(tmt.templates.PLAN, join='or')
@plans.command()
@click.pass_context
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    help='Plan template ({}).'.format(_plan_templates),
    prompt='Template ({})'.format(_plan_templates))
@verbose_debug_quiet
@force_dry
def create(context, name, template, force, **kwargs):
    """ Create a new plan based on given template. """
    tmt.Plan._save_context(context)
    tmt.Plan.create(name, template, context.obj.tree, force)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Story
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@verbose_debug_quiet
def stories(context, **kwargs):
    """
    Manage user stories.

    \b
    Check available user stories.
    Explore coverage (test, implementation, documentation).
    """
    tmt.Story._save_context(context)

    # Show overview of available stories
    if context.invoked_subcommand is None:
        tmt.Story.overview(context.obj.tree)


@stories.command()
@click.pass_context
@name_filter_condition
@implemented_tested_documented
@verbose_debug_quiet
def ls(
    context, implemented, tested, documented, covered,
    unimplemented, untested, undocumented, uncovered, **kwargs):
    """
    List available stories

    Regular expression can be used to filter stories by name.
    Use '.' to select stories under the current working directory.
    """
    tmt.Story._save_context(context)
    for story in context.obj.tree.stories():
        if story._match(implemented, tested, documented, covered,
                unimplemented, untested, undocumented, uncovered):
            story.ls()


@stories.command()
@click.pass_context
@name_filter_condition
@implemented_tested_documented
@verbose_debug_quiet
def show(
    context, implemented, tested, documented, covered,
    unimplemented, untested, undocumented, uncovered, **kwargs):
    """
    Show story details

    Regular expression can be used to filter stories by name.
    Use '.' to select stories under the current working directory.
    """
    tmt.Story._save_context(context)
    for story in context.obj.tree.stories():
        if story._match(implemented, tested, documented, covered,
                unimplemented, untested, undocumented, uncovered):
            story.show()
            echo()


_story_templates = listed(tmt.templates.STORY, join='or')
@stories.command()
@click.pass_context
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    prompt='Template ({})'.format(_story_templates),
    help='Story template ({}).'.format(_story_templates))
@verbose_debug_quiet
@force_dry
def create(context, name, template, force, **kwargs):
    """ Create a new story based on given template. """
    tmt.Story._save_context(context)
    tmt.base.Story.create(name, template, context.obj.tree, force)


@stories.command()
@click.option(
    '--docs', is_flag=True, help='Show docs coverage.')
@click.option(
    '--test', is_flag=True, help='Show test coverage.')
@click.option(
    '--code', is_flag=True, help='Show code coverage.')
@click.pass_context
@name_filter_condition
@implemented_tested_documented
@verbose_debug_quiet
def coverage(
    context, code, test, docs,
    implemented, tested, documented, covered,
    unimplemented, untested, undocumented, uncovered, **kwargs):
    """
    Show code, test and docs coverage for given stories

    Regular expression can be used to filter stories by name.
    Use '.' to select stories under the current working directory.
    """
    tmt.Story._save_context(context)

    def headfoot(text):
        """ Format simple header/footer """
        echo(style(text.rjust(4) + ' ', fg='blue'), nl=False)

    header = False
    total = code_coverage = test_coverage = docs_coverage = 0
    if not any([code, test, docs]):
        code = test = docs = True
    for story in context.obj.tree.stories():
        # Header
        if not header:
            if code:
                headfoot('code')
            if test:
                headfoot('test')
            if docs:
                headfoot('docs')
            headfoot('story')
            echo()
            header = True
        # Coverage
        if story._match(implemented, tested, documented, covered,
                unimplemented, untested, undocumented, uncovered):
            status = story.coverage(code, test, docs)
            total += 1
            code_coverage += status[0]
            test_coverage += status[1]
            docs_coverage += status[2]
    # Summary
    if code:
        headfoot('{}%'.format(round(100 * code_coverage / total)))
    if test:
        headfoot('{}%'.format(round(100 * test_coverage / total)))
    if docs:
        headfoot('{}%'.format(round(100 * docs_coverage / total)))
    headfoot('from {}'.format(listed(total, 'story')))
    echo()


@stories.command()
@click.pass_context
@name_filter_condition
@implemented_tested_documented
@click.option(
    '--format', 'format_', default='rst', show_default=True, metavar='FORMAT',
    help='Output format.')
@click.option(
    '-d', '--debug', is_flag=True,
    help='Provide as much debugging details as possible.')
def export(
    context, format_,
    implemented, tested, documented, covered,
    unimplemented, untested, undocumented, uncovered, **kwargs):
    """
    Export selected stories into desired format

    Regular expression can be used to filter stories by name.
    Use '.' to select stories under the current working directory.
    """
    tmt.Story._save_context(context)

    for story in context.obj.tree.stories(whole=True):
        if story._match(implemented, tested, documented, covered,
                unimplemented, untested, undocumented, uncovered):
            echo(story.export(format_))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Init
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

_init_template_choices = ['empty', 'mini', 'base', 'full']
_init_templates = listed(_init_template_choices, join='or')
@main.command()
@click.pass_context
@click.argument('path', default='.')
@click.option(
    '-t', '--template', default='empty', metavar='TEMPLATE',
    type=click.Choice(_init_template_choices),
    help='Template ({}).'.format(_init_templates))
@verbose_debug_quiet
@force_dry
def init(context, path, template, force, **kwargs):
    """
    Initialize a new tmt tree.

    By default tree is created in the current directory.
    Provide a PATH to create it in a different location.

    \b
    A tree can be optionally populated with example metadata:
    * 'mini' template contains a minimal plan and no tests,
    * 'base' template contains a plan and a beakerlib test,
    * 'full' template contains a 'full' story, an 'full' plan and a shell test.
    """

    # Check for existing tree
    path = os.path.realpath(path)
    try:
        tree = tmt.Tree(path)
        # Are we creating a new tree under the existing one?
        if path == tree.root:
            echo("Tree '{}' already exists.".format(tree.root))
        else:
            tree = None
    except tmt.utils.GeneralError:
        tree = None
    # Create a new tree
    if tree is None:
        try:
            fmf.Tree.init(path)
            tree = tmt.Tree(path)
        except fmf.utils.GeneralError as error:
            raise tmt.utils.GeneralError(
                "Failed to initialize tree in '{}': {}".format(
                    path, error))
        echo("Tree '{}' initialized.".format(tree.root))

    # Populate the tree with example objects if requested
    if template == 'empty':
        non_empty_choices = [c for c in _init_template_choices if c != 'empty']
        echo("To populate it with example content, use --template with "
             "{}.".format(listed(non_empty_choices, join='or')))
    else:
        echo("Applying template '{}'.".format(template, _init_templates))
    if template == 'mini':
        tmt.Plan.create('/plans/example', 'mini', tree, force)
    elif template == 'base':
        tmt.Test.create('/tests/example', 'beakerlib', tree, force)
        tmt.Plan.create('/plans/example', 'base', tree, force)
    elif template == 'full':
        tmt.Test.create('/tests/example', 'shell', tree, force)
        tmt.Plan.create('/plans/example', 'full', tree, force)
        tmt.Story.create('/stories/example', 'full', tree, force)
