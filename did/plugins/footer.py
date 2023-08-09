# coding: utf-8

"""
Customizable footer

Config example::

    [footer]
    type = footer
    next = Plans, thoughts, ideas...
    status = Status: Green | Yellow | Orange | Red

New line characters can be used in the definition as well. In this way
it's possible to define subitems::

    [footer]
    type = footer
    nested = Main topic\\n  * Item one\\n  * Item two\\n  * Item three

Will produce the following output::

    * Main topic
      * Item one
      * Item two
      * Item three
"""

from did.stats import EmptyStatsGroup

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Footer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Footer(EmptyStatsGroup):
    """ Footer """
    # Show footer at the bottom
    order = 900
