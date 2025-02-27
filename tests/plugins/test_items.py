# coding: utf-8
""" Tests for the items plugin """

import did.base
import did.plugins.items

PROJ = 0
TASKS = 1

CONFIG = f"""{did.base.Config.example()}
[projects]
type = items
header = Work on projects
item1 = Project One
item2 = Project Two
item3 = Project Three

[tasks]
type = items
header = Work on tasks
# order screwed on purpose to check it gets reordered!
item3 = Task Three
item1 = Task One
item2 = Task Two
"""


def test_item_plugin():
    did.base.Config(CONFIG)
    stats = did.plugins.items.CustomStats("this-is-getting-ignored")
    stats.check()
    assert len(stats.stats) == 2
    assert stats.stats[PROJ].name == "Work on projects"
    assert stats.stats[PROJ].stats == ['Project One', 'Project Two', 'Project Three']
    assert stats.stats[TASKS].name == "Work on tasks"
    assert stats.stats[TASKS].stats == ['Task One', 'Task Two', 'Task Three']
    assert stats.header() is None
