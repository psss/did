# coding: utf-8
"""
Customizable header

Config example::

    [header]
    type = header
    highlights = Highlights
    joy = Joy of the week ;-)
"""

from status_report.base import EmptyStatsGroup

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Header
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Header(EmptyStatsGroup):
    """ Header """
    # Show header at the top
    order = 0
