# coding: utf-8

""" Common options and the MethodCommand class """

import re

import click

# Verbose, debug and quiet output
verbose_debug_quiet = [
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
force_dry = [
    click.option(
        '-f', '--force', is_flag=True,
        help='Overwrite existing files and step data.'),
    click.option(
        '-n', '--dry', is_flag=True,
        help='Run in dry mode. No changes, please.'),
    ]

fix = click.option(
    '-f', '--fix', is_flag=True,
    help='Attempt to fix all discovered issues.')


def create_method_class(methods):
    """
    Create special class to handle different options for each method

    Accepts dictionary with method names and corresponding commands:
    For example: {'fmf', <click.core.Command object at 0x7f3fe04fded0>}
    Methods should be already sorted according to their priority.
    """

    class MethodCommand(click.Command):
        _method = None

        def _check_method(self, args):
            """ Manually parse the --how option """
            how = None

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

            # Find method with the first matching prefix
            if how is not None:
                for method in methods:
                    if method.startswith(how):
                        self._method = methods[method]
                        break

        def parse_args(self, context, args):
            self._check_method(args)
            if self._method is not None:
                return self._method.parse_args(context, args)
            return super().parse_args(context, args)

        def get_help(self, context):
            if self._method is not None:
                return self._method.get_help(context)
            return super().get_help(context)

        def invoke(self, context):
            if self._method:
                return self._method.invoke(context)
            return super().invoke(context)

    return MethodCommand
