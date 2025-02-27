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

from did.base import Config
from did.stats import Stats, StatsGroup
from did.utils import item

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Custom Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ItemStats(Stats):
    """ Custom section with given items """

    def __init__(self, option: str, name: str = None, parent: StatsGroup = None):
        # Prepare sorted item content from the config section
        items = Config().section(
            option.replace("-item", ""), skip=["type", "header", "order"]
            )
        super().__init__(option, name, parent)
        # items can use '|' as first character to preserve
        # indentation in multiline values
        self._items = [
            value.replace("\n|", "\n")
            for _, value in sorted(items, key=lambda x: x[0])
            ]

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
        super().__init__(option, name, parent, user)
        self.stats.append(
            ItemStats(
                option=f"{option}-item",
                name=Config().item(option, "header"),
                parent=self
                )
            )
