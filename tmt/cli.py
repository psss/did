# coding: utf-8

""" Command line interface for the Test Metadata Tool """

from click import echo, style

import fmf.utils
import click
import os

import tmt
import tmt.utils
import tmt.convert
import tmt.steps

log = fmf.utils.Logging('tmt').logger

# Shared metadata tree
tree = None


class KeepOrderGroup(click.Group):
    """ Custom group to prevent alphabetical sorting """
    def list_commands(self, context):
        return self.commands.keys()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(cls=KeepOrderGroup)
@click.option(
    '--path', metavar='PATH',
    default='.', show_default=True,
    help='Path to the metadata tree.')
def main(path):
    """ Test Metadata Tool """
    # Initialize metadata tree
    try:
        global tree
        tree = tmt.Tree(path)
    except fmf.utils.RootError:
        raise tmt.utils.GeneralError(
            "No metadata found in the '{0}' directory.".format(tree_path))

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Run
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(chain=True, invoke_without_command=True, cls=KeepOrderGroup)
@click.pass_context
def run(context):
    """ Run test steps. """
    # All test steps are enabled if no step selected
    enabled = context.invoked_subcommand is None
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

@click.group(cls=KeepOrderGroup)
def test():
    """
    Manage tests (L1 metadata).

    Check available tests, inspect their metadata.
    Convert old metadata into the new fmf format.
    """

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
#  Testset
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(cls=KeepOrderGroup)
def testset():
    """
    Manage testsets (L2 metadata).

    \b
    Search for available testsets.
    Explore detailed test step configuration.
    """

main.add_command(testset)


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@testset.command()
def ls(names):
    """ List available testsets. """
    for testset in tree.testsets(names=names):
        testset.ls()
    return 'testset ls'


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@testset.command()
def show(names):
    """ Show testset details. """
    for testset in tree.testsets(names=names):
        testset.show()
        echo()
    return 'testset show'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Story
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(cls=KeepOrderGroup)
def story():
    """
    Manage user stories.

    \b
    Check available user stories.
    Explore coverage (test, implementation, documentation).
    """

main.add_command(story)


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@story.command()
def ls(names):
    """ List available stories. """
    for story in tree.stories(names=names):
        story.ls()
    return 'story ls'


@click.argument('names', nargs=-1, metavar='[REGEXP]...')
@story.command()
def show(names):
    """ Show story details. """
    for story in tree.stories(names=names):
        story.show()
        echo()
    return 'story show'



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Go
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def go():
    """ Go and do test steps for selected testsets """
    echo(style('Found {0}.'.format(
        fmf.utils.listed(tree.testsets(), 'testset')), fg='magenta'))
    for testset in tree.testsets():
        echo()
        testset.show()
        testset.go()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Finito
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.resultcallback()
def finito(commands, *args, **kwargs):
    """ Process the main callback """
    # Show all commands that have been provided
    log.info('Detected {0}{1}.'.format(
        fmf.utils.listed(commands, 'command'),
        (': ' + fmf.utils.listed(commands)) if commands else ''))

    # Run test steps if any explicitly requested or no command given at all
    if not commands or any([step in commands for step in tmt.steps.STEPS]):
        go()
