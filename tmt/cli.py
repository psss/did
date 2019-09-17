# coding: utf-8

""" Command line interface for the Test Metadata Tool """

from __future__ import unicode_literals, absolute_import, print_function

import tmt
import tmt.steps
import fmf.utils
import click

tree_path = '.'

# Disable unicode_literals warning
click.disable_unicode_literals_warning = True

@click.group(chain=True, invoke_without_command=True)
@click.pass_context
@click.option(
    '--path', metavar='PATH',
    default='.', show_default=True,
    help='Path to the metadata tree')
def main(ctx, path):
    """ Main command """
    # All test steps are enabled if no step selected
    enabled = ctx.invoked_subcommand is None
    tmt.steps.Discover.enabled = enabled
    tmt.steps.Provision.enabled = enabled
    tmt.steps.Prepare.enabled = enabled
    tmt.steps.Execute.enabled = enabled
    tmt.steps.Report.enabled = enabled
    tmt.steps.Finish.enabled = enabled
    # Update metadata tree path
    global tree_path
    tree_path = path


@main.command()
def discover():
    """ Gather and show information about test cases to be executed """
    tmt.steps.Discover.enabled = True


@main.command()
def provision():
    """ Provision an environment for testing (or use localhost) """
    tmt.steps.Provision.enabled = True


@main.command()
def prepare():
    """ Configure environment for testing (like ansible playbook) """
    tmt.steps.Prepare.enabled = True


@main.command()
def execute():
    """ Run the tests (using the specified framework and its settings) """
    tmt.steps.Execute.enabled = True


@main.command()
def report():
    """ Provide an overview of test results and send notifications """
    tmt.steps.Report.enabled = True


@main.command()
def finish():
    """ Additional actions to be performed after the test execution """
    tmt.steps.Finish.enabled = True


@main.resultcallback()
def finito(*args, **kwargs):
    try:
        tree = tmt.Tree(tree_path)
    except fmf.utils.RootError:
        raise fmf.utils.RootError(
            "No metadata found in the '{0}' directory.".format(tree_path))

    click.echo(click.style('Found {0}.'.format(
        fmf.utils.listed(tree.testsets, 'testset')), fg='magenta'))
    for testset in tree.testsets:
        click.echo(click.style(
            '\nTestset: {0}'.format(testset), fg='green'))
        testset.go()
