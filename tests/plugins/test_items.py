# coding: utf-8
""" Tests for the items plugin """

import did.base
import did.plugins.items
import did.stats

PROJ = 0
TASKS = 1

CONFIG = f"""{did.base.Config.example()}
[projects]
type = items
order = 10
header = Work on projects
item1 = Project One
item2 = Project Two
item3 = Project Three
item4 = Project Four
        |    * with indentation

[tasks]
type = items
order = 20
header = Work on tasks
# order screwed on purpose to check it gets reordered!
item3 = Task Three
item1 = Task One
item2 = Task Two
"""


def test_item_with_indented_content():
    did.base.Config(CONFIG)
    stats = did.plugins.items.CustomStats("projects")
    stats.check()
    assert len(stats.stats) == 1
    assert stats.stats[0].name == "Work on projects"
    assert stats.stats[0].stats == [
        'Project One',
        'Project Two',
        'Project Three',
        'Project Four\n    * with indentation'
        ]


def test_item_with_wrongly_ordered_content():
    did.base.Config(CONFIG)
    stats = did.plugins.items.CustomStats("tasks")
    stats.check()
    assert len(stats.stats) == 1
    assert stats.stats[0].name == "Work on tasks"
    assert stats.stats[0].stats == ['Task One', 'Task Two', 'Task Three']
    assert stats.header() is None


def test_items_ordering():
    config = did.base.Config(CONFIG)
    user_stats = did.stats.UserStats(
        user=did.base.User(email=config.email), config=config
        )
    user_stats.check()
    assert len(user_stats.stats) == 2
    assert user_stats.stats[PROJ].order == 10
    assert user_stats.stats[TASKS].order == 20
