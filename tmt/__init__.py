""" Test Management Tool """

# Version is replaced before building the package
__version__ = 'running from the source'

__all__ = ['Tree', 'Test', 'Plan', 'Story', 'Run', 'Guest', 'Result',
           'Status', 'Clean']

from tmt.base import Tree, Test, Plan, Story, Run, Result, Status, Clean
from tmt.steps.provision import Guest
