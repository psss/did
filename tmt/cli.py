# coding: utf-8

""" Command line interface for the Test Metadata Tool """

from __future__ import unicode_literals, absolute_import, print_function

import fmf.utils
import click
import os

import tmt
import tmt.utils
import tmt.convert
import tmt.steps

log = fmf.utils.Logging('tmt').logger

tree_path = '.'

# Disable unicode_literals warning
click.disable_unicode_literals_warning = True

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group()
@click.option(
    '--path', metavar='PATH',
    default='.', show_default=True,
    help='Path to the metadata tree.')
def main(path):
    """ Test Metadata Tool """
    global tree_path
    tree_path = path

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Run
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(chain=True, invoke_without_command=True)
@click.pass_context
def run(context):
    """ Run test steps (discover, prepare, execute...) """
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

@click.group()
@click.pass_context
def test(context):
    """
    Handle test metadata (investigate, filter, convert).

    Check available tests, inspect their metadata, gather old metadata from
    various sources and stored them in the new fmf format.
    """

main.add_command(test)


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
#  Go
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def go():
    """ Go and do test steps for selected testsets """
    # Initialize metadata tree, check available testsets
    try:
        tree = tmt.Tree(tree_path)
    except fmf.utils.RootError:
        raise tmt.utils.GeneralError(
            "No metadata found in the '{0}' directory.".format(tree_path))
    click.echo(click.style('Found {0}.'.format(
        fmf.utils.listed(tree.testsets, 'testset')), fg='magenta'))

    # Go and do selected steps for each testset
    for testset in tree.testsets:
        click.echo(click.style('\nTestset: {0}'.format(testset), fg='green'))
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