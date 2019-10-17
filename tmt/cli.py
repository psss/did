# coding: utf-8

""" Command line interface for the Test Management Tool """

from click import echo, style
from fmf.utils import listed

import click
import os
import re

import fmf
import tmt
import tmt.utils
import tmt.convert
import tmt.steps
import tmt.templates

log = fmf.utils.Logging('tmt').logger

# Shared metadata tree
tree = None


class CustomGroup(click.Group):
    """ Custom Click Group """

    def list_commands(self, context):
        """ Prevent alphabetical sorting """
        return self.commands.keys()

    def get_command(self, context, cmd_name):
        """ Allow command shortening """
        # Support both story & stories
        cmd_name = re.sub('story', 'stories', cmd_name)
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
#  Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@click.option(
    '--path', metavar='PATH', default='.', show_default=True,
    help='Path to the metadata tree.')
def main(context, path):
    """ Test Management Tool """
    # Initialize metadata tree
    global tree
    tree = tmt.Tree(path)

    # Show overview of available tests, plans and stories
    if context.invoked_subcommand is None:
        tmt.Test.overview()
        tmt.Plan.overview()
        tmt.Story.overview()

    return 'tmt'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Run
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(chain=True, invoke_without_command=True, cls=CustomGroup)
@click.option(
    '-a', '--all', 'all_', help='Run all steps, customize some', is_flag=True)
@click.pass_context
def run(context, all_):
    """ Run test steps. """
    # All test steps are enabled if no step selected
    enabled = context.invoked_subcommand is None or all_
    tmt.steps.Discover.enabled = enabled
    tmt.steps.Provision.enabled = enabled
    tmt.steps.Prepare.enabled = enabled
    tmt.steps.Execute.enabled = enabled
    tmt.steps.Report.enabled = enabled
    tmt.steps.Finish.enabled = enabled
    # Update metadata tree path

main.add_command(run)


@run.command()
def discover():
    """ Gather and show information about test cases to be executed """
    tmt.steps.Discover.enabled = True
    return 'discover'


@run.command()
def provision():
    """ Provision an environment for testing (or use localhost) """
    tmt.steps.Provision.enabled = True
    return 'provision'


@run.command()
def prepare():
    """ Configure environment for testing (like ansible playbook) """
    tmt.steps.Prepare.enabled = True
    return 'prepare'


@run.command()
def execute():
    """ Run the tests (using the specified framework and its settings) """
    tmt.steps.Execute.enabled = True
    return 'execute'


@run.command()
def report():
    """ Provide an overview of test results and send notifications """
    tmt.steps.Report.enabled = True
    return 'report'


@run.command()
def finish():
    """ Additional actions to be performed after the test execution """
    tmt.steps.Finish.enabled = True
    return 'finish'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Test
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
def tests(context):
    """
    Manage tests (L1 metadata).

    Check available tests, inspect their metadata.
    Convert old metadata into the new fmf format.
    """

    # Show overview of available tests
    if context.invoked_subcommand is None:
        tmt.Test.overview()

    return 'test'

main.add_command(tests)


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@tests.command()
def ls(names):
    """ List available tests. """
    for test in tree.tests(names=names):
        test.ls()
    return 'test ls'


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@click.option(
    '-v', '--verbose', is_flag=True,
    help='Show source files where metadata are stored.')
@tests.command()
def show(names, verbose):
    """ Show test details. """
    for test in tree.tests(names=names):
        test.show(verbose)
        echo()
    return 'test show'


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@tests.command()
def lint(names):
    """ Check tests against the L1 metadata specification. """
    for test in tree.tests(names=names):
        test.lint()
        echo()
    return 'test lint'


_test_templates = listed(tmt.templates.TEST, join='or')
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    help='Test template ({}).'.format(_test_templates),
    prompt='Template ({})'.format(_test_templates))
@click.option(
    '-f', '--force', help='Force overwriting existing files.',
    is_flag=True)
@tests.command()
def create(name, template, force):
    """ Create a new test based on given template. """
    tmt.Test.create(name, template, force)
    return 'test create'


@click.option(
    '--nitrate / --no-nitrate', default=True,
    help='Import test metadata from Nitrate')
@click.option(
    '--purpose / --no-purpose', default=True,
    help='Migrate description from PURPOSE file')
@click.option(
    '--makefile / --no-makefile', default=True,
    help='Convert Beaker Makefile metadata')
@click.argument('paths', nargs=-1, metavar='[PATH]...')
@tests.command()
def convert(paths, makefile, nitrate, purpose):
    """
    Convert old test metadata into the new fmf format.

    Accepts one or more directories where old metadata are stored.
    By default all available sources and current directory are used.
    The following test metadata are converted for each source:

    \b
    makefile ..... summary, component, duration
    purpose ...... description
    nitrate ...... environment, relevancy
    """
    if not paths:
        paths = ['.']
    for path in paths:
        # Make sure we've got a real directory
        path = os.path.realpath(path)
        if not os.path.isdir(path):
            raise tmt.utils.GeneralError(
                "Path '{0}' is not a directory.".format(path))
        # Gather old metadata and store them as fmf
        data = tmt.convert.read(path, makefile, nitrate, purpose)
        tmt.convert.write(path, data)
    return 'convert'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Plan
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
def plans(context):
    """
    Manage test plans (L2 metadata).

    \b
    Search for available plans.
    Explore detailed test step configuration.
    """

    # Show overview of available plans
    if context.invoked_subcommand is None:
        tmt.Plan.overview()

    return 'plan'


main.add_command(plans)


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@plans.command()
def ls(names):
    """ List available plans. """
    for plan in tree.plans(names=names):
        plan.ls()
    return 'plan ls'


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@click.option(
    '-v', '--verbose', is_flag=True,
    help='Show source files where metadata are stored.')
@plans.command()
def show(names, verbose):
    """ Show plan details. """
    for plan in tree.plans(names=names):
        plan.show(verbose)
        echo()
    return 'plan show'


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@plans.command()
def lint(names):
    """ Check plans against the L2 metadata specification. """
    for plan in tree.plans(names=names):
        plan.lint()
        echo()
    return 'plan lint'


_plan_templates = listed(tmt.templates.PLAN, join='or')
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    help='Plan template ({}).'.format(_plan_templates),
    prompt='Template ({})'.format(_plan_templates))
@click.option(
    '-f', '--force', help='Force overwriting existing files.',
    is_flag=True)
@plans.command()
def create(name, template, force):
    """ Create a new plan based on given template. """
    tmt.Plan.create(name, template, force)
    return 'plan create'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Story
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
def stories(context):
    """
    Manage user stories.

    \b
    Check available user stories.
    Explore coverage (test, implementation, documentation).
    """

    # Show overview of available stories
    if context.invoked_subcommand is None:
        tmt.Story.overview()

    return 'test'

main.add_command(stories)


@click.option(
    '--undocumented', is_flag=True, help='Undocumented stories only.')
@click.option(
    '--untested', is_flag=True, help='Untested stories only.')
@click.option(
    '--unimplemented', is_flag=True, help='Unimplemented stories only.')
@click.option(
    '-u', '--uncovered', is_flag=True, help='Uncovered stories only.')
@click.option(
    '-c', '--covered', is_flag=True, help='Covered stories only.')
@click.option(
    '-d', '--documented', is_flag=True, help='Documented stories only.')
@click.option(
    '-t', '--tested', is_flag=True, help='Tested stories only.')
@click.option(
    '-i', '--implemented', is_flag=True, help='Implemented stories only.')
@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@stories.command()
def ls(
    names, implemented, tested, documented, covered,
    unimplemented, untested, undocumented, uncovered):
    """ List available stories. """
    for story in tree.stories(names=names):
        if story._match(implemented, tested, documented, covered,
                unimplemented, untested, undocumented, uncovered):
            story.ls()
    return 'story ls'


@click.option(
    '-v', '--verbose', is_flag=True,
    help='Show source files where metadata are stored.')
@click.option(
    '--undocumented', is_flag=True, help='Undocumented stories only.')
@click.option(
    '--untested', is_flag=True, help='Untested stories only.')
@click.option(
    '--unimplemented', is_flag=True, help='Unimplemented stories only.')
@click.option(
    '-u', '--uncovered', is_flag=True, help='Uncovered stories only.')
@click.option(
    '-c', '--covered', is_flag=True, help='Covered stories only.')
@click.option(
    '-d', '--documented', is_flag=True, help='Documented stories only.')
@click.option(
    '-t', '--tested', is_flag=True, help='Tested stories only.')
@click.option(
    '-i', '--implemented', is_flag=True, help='Implemented stories only.')
@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@stories.command()
def show(
    names, implemented, tested, documented, covered,
    unimplemented, untested, undocumented, uncovered, verbose):
    """ Show story details. """
    for story in tree.stories(names=names):
        if story._match(implemented, tested, documented, covered,
                unimplemented, untested, undocumented, uncovered):
            story.show(verbose)
            echo()
    return 'story show'


_story_templates = listed(tmt.templates.STORY, join='or')
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    prompt='Template ({})'.format(_story_templates),
    help='Story template ({}).'.format(_story_templates))
@click.option(
    '-f', '--force', help='Force overwriting existing files.',
    is_flag=True)
@stories.command()
def create(name, template, force):
    """ Create a new story based on given template. """
    tmt.base.Story.create(name, template, force)
    return 'story create'


@click.option(
    '--undocumented', is_flag=True, help='Undocumented stories only.')
@click.option(
    '--untested', is_flag=True, help='Untested stories only.')
@click.option(
    '--unimplemented', is_flag=True, help='Unimplemented stories only.')
@click.option(
    '--uncovered', is_flag=True, help='Uncovered stories only.')
@click.option(
    '--covered', is_flag=True, help='Covered stories only.')
@click.option(
    '--documented', is_flag=True, help='Documented stories only.')
@click.option(
    '--tested', is_flag=True, help='Tested stories only.')
@click.option(
    '--implemented', is_flag=True, help='Implemented stories only.')
@click.option(
    '-d', '--docs', is_flag=True, help='Show docs coverage.')
@click.option(
    '-t', '--test', is_flag=True, help='Show test coverage.')
@click.option(
    '-c', '--code', is_flag=True, help='Show code coverage.')
@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@stories.command()
def coverage(
    names, code, test, docs,
    implemented, tested, documented, covered,
    unimplemented, untested, undocumented, uncovered):
    """ Show code, test and docs coverage for given stories. """

    def headfoot(text):
        """ Format simple header/footer """
        echo(style(text.rjust(4) + ' ', fg='blue'), nl=False)

    header = False
    total = code_coverage = test_coverage = docs_coverage = 0
    if not any([code, test, docs]):
        code = test = docs = True
    for story in tree.stories(names=names):
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

    return 'story coverage'


@click.option(
    '--undocumented', is_flag=True, help='Undocumented stories only.')
@click.option(
    '--untested', is_flag=True, help='Untested stories only.')
@click.option(
    '--unimplemented', is_flag=True, help='Unimplemented stories only.')
@click.option(
    '-u', '--uncovered', is_flag=True, help='Uncovered stories only.')
@click.option(
    '-c', '--covered', is_flag=True, help='Covered stories only.')
@click.option(
    '-d', '--documented', is_flag=True, help='Documented stories only.')
@click.option(
    '-t', '--tested', is_flag=True, help='Tested stories only.')
@click.option(
    '-i', '--implemented', is_flag=True, help='Implemented stories only.')
@click.option(
    '--format', 'format_', default='rst', show_default=True, metavar='FORMAT',
    help='Output format.')
@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@stories.command()
def export(
    names, format_,
    implemented, tested, documented, covered,
    unimplemented, untested, undocumented, uncovered):
    """ Export selected stories into desired format. """

    for story in tree.stories(names=names, whole=True):
        if story._match(implemented, tested, documented, covered,
                unimplemented, untested, undocumented, uncovered):
            echo(story.export(format_))

    return 'story export'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Init
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.argument('path', default='.')
@click.option('--mini', is_flag=True, help='Create simple set of examples.')
@click.option('--full', is_flag=True, help='Create full set of examples.')
@click.option(
    '-f', '--force', is_flag=True, help='Create full set of examples.')
@main.command()
def init(path, mini, full, force):
    """ Initialize the tree root. """

    # Initialize the FMF metadata tree root
    try:
        tree = fmf.Tree(path)
        echo("Tree root '{}' already exists.".format(tree.root))
    except fmf.utils.RootError:
        try:
            root = fmf.Tree.init(path)
        except fmf.utils.GeneralError as error:
            raise tmt.utils.GeneralError(
                "Failed to initialize tree root in '{}': {}".format(
                    path, error))
        echo("Tree root '{}' initialized.".format(root))

    # Populate the tree with example objects if requested
    if mini:
        tmt.Test.create('/tests/example', 'shell', force)
        tmt.Plan.create('/plans/example', 'mini', force)
        tmt.Story.create('/stories/example', 'mini', force)
    if full:
        tmt.Test.create('/tests/example', 'shell', force)
        tmt.Plan.create('/plans/example', 'full', force)
        tmt.Story.create('/stories/example', 'full', force)

    return 'init'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Go
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def go():
    """ Go and do test steps for selected plans """
    echo(style('Found {0}.\n'.format(
        listed(tree.plans(), 'plan')), fg='magenta'))
    for plan in tree.plans():
        plan.ls(summary=True)
        plan.go()
        echo()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Finito
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.resultcallback()
def finito(commands, *args, **kwargs):
    """ Process the main callback """
    # Show all commands that have been provided
    log.info('Detected {0}{1}.'.format(
        listed(commands, 'command'),
        (': ' + listed(commands)) if commands else ''))

    # Run test steps if any explicitly requested or no command given at all
    if not commands or any([step in commands for step in tmt.steps.STEPS]):
        go()
