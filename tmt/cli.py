# coding: utf-8

""" Command line interface for the Test Metadata Tool """

from __future__ import unicode_literals, absolute_import, print_function

import tmt
import tmt.steps
import fmf.utils
import click

tree_path = '.'


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
    """ Gather information about test cases to be run """
    tmt.steps.Discover.enabled = True


@main.command()
def provision():
    """ Information about environment needed for testing """
    tmt.steps.Provision.enabled = True


@main.command()
def prepare():
    """ Additional configuration of the test environment """
    tmt.steps.Prepare.enabled = True


@main.command()
def execute():
    """ Execution of individual test cases """
    tmt.steps.Execute.enabled = True


@main.command()
def report():
    """ Notifications about the test progress and results """
    tmt.steps.Report.enabled = True


@main.command()
def finish():
    """ Actions performed after test execution is completed """
    tmt.steps.Finish.enabled = True


@main.resultcallback()
def finito(*args, **kwargs):
    tree = tmt.Tree(tree_path)
    click.echo(click.style('Found {0}.'.format(
        fmf.utils.listed(tree.testsets, 'testset')), fg='magenta'))
    for testset in tree.testsets:
        click.echo(click.style(
            '\nTestset: {0}'.format(testset), fg='green'))
        testset.go()
