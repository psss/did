# coding: utf-8

""" Common options and the MethodCommand class """

import re
from typing import Any, Callable, Dict, List, Optional, Type

import click

import tmt.utils

MethodDictType = Dict[str, click.core.Command]
# Originating in click.decorators, an opaque type describing "decorator" functions
# produced by click.option() calls: not options, but rather functions that attach
# options to a given command.
ClickOptionDecoratorType = Callable[[Callable[..., Any]], Any]

# Verbose, debug and quiet output
verbose_debug_quiet: List[ClickOptionDecoratorType] = [
    click.option(
        '-v', '--verbose', count=True, default=0,
        help='Show more details. Use multiple times to raise verbosity.'),
    click.option(
        '-d', '--debug', count=True, default=0,
        help='Provide debugging information. Repeat to see more details.'),
    click.option(
        '-q', '--quiet', is_flag=True,
        help='Be quiet. Exit code is just enough for me.'),
    ]

# Force and dry actions
force_dry: List[ClickOptionDecoratorType] = [
    click.option(
        '-f', '--force', is_flag=True,
        help='Overwrite existing files and step data.'),
    click.option(
        '-n', '--dry', is_flag=True,
        help='Run in dry mode. No changes, please.'),
    ]

# Fix action
fix = click.option(
    '-F', '--fix', is_flag=True,
    help='Attempt to fix all discovered issues.')


def show_step_method_hints(
        log_object: tmt.utils.Common,
        step_name: str,
        how: str) -> None:
    """
    Show hints about available step methods' installation

    The log_object will be used to output the hints to the terminal, hence
    it must be an instance of a subclass of tmt.utils.Common (info method
    must be available).
    """
    if step_name == 'provision':
        if how == 'virtual':
            log_object.info(
                'hint', "Install 'tmt-provision-virtual' "
                        "to run tests in a virtual machine.", color='blue')
        if how == 'container':
            log_object.info(
                'hint', "Install 'tmt-provision-container' "
                        "to run tests in a container.", color='blue')
        if how == 'minute':
            log_object.info(
                'hint', "Install 'tmt-redhat-provision-minute' "
                        "to run tests in 1minutetip OpenStack backend. "
                        "(Available only from the internal COPR repository.)",
                        color='blue')
        log_object.info(
            'hint', "Use the 'local' method to execute tests "
                    "directly on your localhost.", color='blue')
        log_object.info(
            'hint', "See 'tmt run provision --help' for all "
                    "available provision options.", color='blue')
    elif step_name == 'report':
        if how == 'html':
            log_object.info(
                'hint', "Install 'tmt-report-html' to format results "
                        "as a html report.", color='blue')
        if how == 'junit':
            log_object.info(
                'hint', "Install 'tmt-report-junit' to write results "
                        "in JUnit format.", color='blue')
        log_object.info(
            'hint', "Use the 'display' method to show test results "
                    "on the terminal.", color='blue')
        log_object.info(
            'hint', "See 'tmt run report --help' for all "
                    "available report options.", color='blue')


def create_method_class(methods: MethodDictType) -> Type[click.Command]:
    """
    Create special class to handle different options for each method

    Accepts dictionary with method names and corresponding commands:
    For example: {'fmf', <click.core.Command object at 0x7f3fe04fded0>}
    Methods should be already sorted according to their priority.
    """

    class MethodCommand(click.Command):
        _method: Optional[click.Command] = None

        def _check_method(self, context: click.Context, args: List[str]) -> None:
            """ Manually parse the --how option """
            how = None
            subcommands = (
                tmt.steps.STEPS + tmt.steps.ACTIONS + ['tests', 'plans'])

            for index in range(len(args)):
                # Handle '--how method' or '-h method'
                if args[index] in ['--how', '-h']:
                    try:
                        how = args[index + 1]
                    except IndexError:
                        pass
                    break
                # Handle '--how=method'
                elif args[index].startswith('--how='):
                    how = re.sub('^--how=', '', args[index])
                    break
                # Handle '-hmethod'
                elif args[index].startswith('-h'):
                    how = re.sub('^-h ?', '', args[index])
                    break
                # Stop search at the first argument looking like a subcommand
                elif args[index] in subcommands:
                    break

            # Find method with the first matching prefix
            if how is not None:
                for method in methods:
                    if method.startswith(how):
                        self._method = methods[method]
                        break

            if how and self._method is None:
                # Use run for logging, steps may not be initialized yet
                show_step_method_hints(context.obj.run, self.name, how)
                raise tmt.utils.SpecificationError(
                    f"Unsupported {self.name} method '{how}'.")

        def parse_args(self, context: click.Context, args: List[str]) -> List[str]:
            self._check_method(context, args)
            if self._method is not None:
                return self._method.parse_args(context, args)
            return super().parse_args(context, args)

        def get_help(self, context: click.Context) -> str:
            if self._method is not None:
                return self._method.get_help(context)
            return super().get_help(context)

        def invoke(self, context: click.Context) -> Any:
            if self._method:
                return self._method.invoke(context)
            return super().invoke(context)

    return MethodCommand
