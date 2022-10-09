# coding: utf-8

""" Handle Plugins """

import importlib
import os
import pkgutil
import sys
from typing import Any, Generator, Optional

if sys.version_info < (3, 9):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

import fmf

import tmt
from tmt.steps import STEPS

log = fmf.utils.Logging('tmt').logger

# Two possibilities to load additional plugins:
# entry_points (setup_tools)
ENTRY_POINT_NAME = 'tmt.plugin'
# Directories with module in environment variable
ENVIRONMENT_NAME = 'TMT_PLUGINS'


def explore() -> None:
    """ Explore all available plugins """

    # Check all tmt steps for native plugins
    root = os.path.dirname(os.path.realpath(tmt.__file__))
    for step in STEPS:
        for module in discover(os.path.join(root, 'steps', step)):
            import_(f'tmt.steps.{step}.{module}')
    # Check for possible plugins in the 'plugins' directory
    for module in discover(os.path.join(root, 'plugins')):
        import_(f'tmt.plugins.{module}')

    # Check environment variable for user plugins
    try:
        paths = [
            os.path.realpath(os.path.expandvars(os.path.expanduser(path)))
            for path in os.environ[ENVIRONMENT_NAME].split(os.pathsep)]
    except KeyError:
        log.debug(f'No custom plugin locations detected in {ENVIRONMENT_NAME}.')
        paths = []
    for path in paths:
        for module in discover(path):
            if path not in sys.path:
                sys.path.insert(0, path)
            import_(module, path)

    # Import by entry_points
    try:
        for found in entry_points()[ENTRY_POINT_NAME]:
            log.debug(f'Loading plugin "{found.name}" ({found.value}).')
            found.load()
    except KeyError:
        log.debug(f'No custom plugins detected for "{ENTRY_POINT_NAME}".')


def import_(module: str, path: Optional[str] = None) -> None:
    """ Attempt to import requested module """
    try:
        importlib.import_module(module)
        log.debug(f"Successfully imported the '{module}' module.")
    except ImportError as error:
        raise SystemExit(
            f"Failed to import the '{module}' module" +
            (f" from '{path}'." if path else ".") + f"\n({error})")


def import_member(module_name: str, member_name: str) -> Any:
    """ Import member from given module, handle errors nicely """
    # Make sure the module is imported. It probably is, but really,
    # make sure of it.
    try:
        import_(module_name)
    except SystemExit as exc:
        raise tmt.utils.GeneralError(f"Failed to import module '{module_name}'.") from exc

    # Now the module should be available in `sys.modules` like any
    # other, and we can go and grab the class we need from it.
    if module_name not in sys.modules:
        raise tmt.utils.GeneralError(f"Failed to import module '{module_name}'.")
    module = sys.modules[module_name]

    # Get the member and return it
    if not hasattr(module, member_name):
        raise tmt.utils.GeneralError(f"No such member '{member_name}' in module '{module_name}'.")
    return getattr(module, member_name)


def discover(path: str) -> Generator[str, None, None]:
    """ Discover available plugins for given paths """
    for _, name, package in pkgutil.iter_modules([path]):
        if not package:
            yield name
