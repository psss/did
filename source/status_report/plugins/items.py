# coding: utf-8
""" Comfortably generate reports - Custom Stats """

from status_report.base import Stats, StatsGroup
from status_report.utils import Config, item

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Custom Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ItemStats(Stats):
    """ Custom section with given items """

    def __init__(self, option, name=None, parent=None):
        # Prepare sorted item content from the config section
        items = Config().section(option, skip=["type", "header", "order"])
        self._items = [
            "{0}{1}".format(value, "" if "-" in value else " - ")
            for _, value in sorted(items, key=lambda x: x[0])]
        Stats.__init__(self, option, name, parent)

    def header(self):
        """ Simple header for custom stats (no item count) """
        item(self.name, 0, options=self.options)

    def fetch(self):
        self.stats = self._items


class CustomStats(StatsGroup):
    """ Custom stats """

    # Default order
    order = 800

    def __init__(self, option, name=None, parent=None):
        StatsGroup.__init__(self, "custom", name, parent)
        for section in Config().sections(kind="items"):
            self.stats.append(ItemStats(
                option=section, parent=self,
                name=Config().item(section, "header")))
