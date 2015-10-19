# coding: utf-8
"""
Custom section with multiple items

Config example::

    [projects]
    type = items
    header = Work on projects
    item1 = Project One
    item2 = Project Two
    item3 = Project Three
"""

from did.utils import item
from did.stats import Stats, StatsGroup


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Custom Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ItemStats(Stats):
    """ Custom section with given items """

    def __init__(self, option, name=None, parent=None):
        # Prepare sorted item content from the config section
        items = self.config.section(option, skip=["type", "header", "order"])
        self._items = [
            "{0}{1}".format(value, "" if "-" in value else " - ")
            for _, value in sorted(items, key=lambda x: x[0])]
        super(ItemStats, self).__init__(option, name, parent)

    def header(self):
        """ Simple header for custom stats (no item count) """
        item(self.name, 0, options=self.options)

    def fetch(self):
        self.stats = self._items


class CustomStats(StatsGroup):
    """ Custom stats """

    # Default order
    order = 800

    def __init__(self, option, name=None, parent=None, user=None):
        super(StatsGroup, self).__init__("custom", name, parent, user)
        for section in self.config.sections(kind="items"):
            self.stats.append(ItemStats(
                option=section, parent=self,
                name=self.config.item(section, "header")))
