# coding: utf-8
"""
Customizable header

Config example::

    [header]
    type = header
    highlights = Highlights
    joy = Joy of the week ;-)
"""

from did.stats import EmptyStatsGroup


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Header
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Header(EmptyStatsGroup):
    """ Header """
    # Show header at the top
    order = 0
