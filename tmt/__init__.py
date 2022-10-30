""" Test Management Tool """

# Version is replaced before building the package
__version__ = 'running from the source'

__all__ = [
    'Tree',
    'Test',
    'Plan',
    'Story',
    'Run',
    'Guest',
    'GuestSsh',
    'Result',
    'Status',
    'Clean',
    'Logger']

from tmt.base import Clean, Plan, Run, Status, Story, Test, Tree
from tmt.log import Logger
from tmt.result import Result
from tmt.steps.provision import Guest, GuestSsh
