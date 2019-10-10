# coding: utf-8

""" Command line interface for the Test Metadata Tool """

from click import echo, style
from fmf.utils import listed

import click
import os

import fmf
import tmt
import tmt.base
import tmt.utils
import tmt.convert
import tmt.steps

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
    """ Test Metadata Tool """
    # Initialize metadata tree
    global tree
    tree = tmt.Tree(path)

    # Show overview of available tests, plans and stories
    if context.invoked_subcommand is None:
        tmt.base.Test.overview()
        tmt.base.Plan.overview()
        tmt.base.Story.overview()

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
def test(context):
    """
    Manage tests (L1 metadata).

    Check available tests, inspect their metadata.
    Convert old metadata into the new fmf format.
    """

    # Show overview of available tests
    if context.invoked_subcommand is None:
        tmt.base.Test.overview()

    return 'test'

main.add_command(test)


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@test.command()
def ls(names):
    """ List available tests. """
    for test in tree.tests(names=names):
        test.ls()
    return 'test ls'


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@test.command()
def show(names):
    """ Show test details. """
    for test in tree.tests(names=names):
        test.show()
        echo()
    return 'test show'


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@test.command()
def lint(names):
    """ Check tests against the L1 metadata specification. """
    for test in tree.tests(names=names):
        test.lint()
        echo()
    return 'test lint'


@click.argument('name')
@click.option(
    '-t', '--template', help='Test skeleton (shell or beakerlib).',
    metavar='TEMPLATE', prompt=True)
@click.option(
    '-f', '--force', help='Force overwriting existing files.',
    is_flag=True)
@test.command()
def create(name, template, force):
    """ Create a new test based on given template. """
    tmt.base.Test.create(name, template, force)
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
@test.command()
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
def plan(context):
    """
    Manage test plans (L2 metadata).

    \b
    Search for available plans.
    Explore detailed test step configuration.
    """

    # Show overview of available plans
    if context.invoked_subcommand is None:
        tmt.base.Plan.overview()

    return 'plan'


main.add_command(plan)


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@plan.command()
def ls(names):
    """ List available plans. """
    for plan in tree.plans(names=names):
        plan.ls()
    return 'plan ls'


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@plan.command()
def show(names):
    """ Show plan details. """
    for plan in tree.plans(names=names):
        plan.show()
        echo()
    return 'plan show'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Story
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
def story(context):
    """
    Manage user stories.

    \b
    Check available user stories.
    Explore coverage (test, implementation, documentation).
    """

    # Show overview of available stories
    if context.invoked_subcommand is None:
        tmt.base.Story.overview()

    return 'test'

main.add_command(story)


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
@story.command()
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
@story.command()
def show(
    names, implemented, tested, documented, covered,
    unimplemented, untested, undocumented, uncovered):
    """ Show story details. """
    for story in tree.stories(names=names):
        if story._match(implemented, tested, documented, covered,
                unimplemented, untested, undocumented, uncovered):
            story.show()
            echo()
    return 'story show'


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
@story.command()
def coverage(
    names, code, test, docs,
    implemented, tested, documented, covered,
    unimplemented, untested, undocumented, uncovered):
    """ Show code, test and docs coverage for given stories """

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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Init
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.argument('path', default='.')
@main.command()
def init(path):
    """ Initialize the tree root. """

    try:
        root = fmf.Tree.init(path)
    except fmf.utils.GeneralError as error:
        raise tmt.utils.GeneralError(
                "Failed to initialize tree root in '{}': {}".format(
                    path, error))
    echo("Tree root '{}' initialized.".format(root))

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
