# coding: utf-8
"""
Customizable header

Config example::

    [header]
    type = header
    highlights = Highlights
    joy = Joy of the week ;-)

New line characters can be used in the definition as well. In this way
it's possible to define subitems::

    [header]
    type = header
    nested = Main topic\\n  * Item one\\n  * Item two\\n  * Item three

Will produce the following output::

    * Main topic
      * Item one
      * Item two
      * Item three
"""

from did.stats import EmptyStatsGroup

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Header
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Header(EmptyStatsGroup):
    """ Header """
    # Show header at the top
    order = 0
