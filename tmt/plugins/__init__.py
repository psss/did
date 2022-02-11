# coding: utf-8

""" Handle Plugins """

import importlib
import os
import pkgutil
import sys

import fmf

import tmt

log = fmf.utils.Logging('tmt').logger


def explore():
    """ Explore all available plugins """

    # Check all tmt steps for native plugins
    root = os.path.dirname(os.path.realpath(tmt.__file__))
    for step in tmt.steps.STEPS:
        for module in discover(os.path.join(root, 'steps', step)):
            import_(f'tmt.steps.{step}.{module}')
    # Check for possible plugins in the 'plugins' directory
    for module in discover(os.path.join(root, 'plugins')):
        import_(f'tmt.plugins.{module}')

    # Check environment variable for user plugins
    try:
        paths = [
            os.path.realpath(os.path.expandvars(os.path.expanduser(path)))
            for path in os.environ["TMT_PLUGINS"].split(os.pathsep)]
    except KeyError:
        log.debug('No custom plugin locations detected in TMT_PLUGINS.')
        paths = []
    for path in paths:
        for module in discover(path):
            if path not in sys.path:
                sys.path.insert(0, path)
            import_(module, path)


def import_(module, path=None):
    """ Attempt to import requested module """
    try:
        importlib.import_module(module)
        log.debug(f"Successfully imported the '{module}' module.")
    except ImportError as error:
        raise SystemExit(
            f"Failed to import the '{module}' module" +
            (f" from '{path}'." if path else ".") + f"\n({error})")


def discover(path):
    """ Discover available plugins for given paths """
    for _, name, package in pkgutil.iter_modules([path]):
        if not package:
            yield name
