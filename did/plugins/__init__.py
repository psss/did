"""
Modules in this direcotry are searched for available stats. Each
plugin should contain a single class inheriting from StatsGroup.
Stats from this group will be included in the report if enabled in
user config. Name of the plugin should match config section type.
Attribute ``order`` defines the default order in the final report.

This is the default plugin order:

    +----------+-----+
    | header   | 000 |
    +----------+-----+
    | nitrate  | 100 |
    +----------+-----+
    | bugzilla | 200 |
    +----------+-----+
    | git      | 300 |
    +----------+-----+
    | gerrit   | 350 |
    +----------+-----+
    | trac     | 400 |
    +----------+-----+
    | rt       | 500 |
    +----------+-----+
    | jira     | 600 |
    +----------+-----+
    | wiki     | 700 |
    +----------+-----+
    | items    | 800 |
    +----------+-----+
    | footer   | 900 |
    +----------+-----+

"""

from __future__ import unicode_literals, absolute_import

import os
import sys
import types

from did.utils import log
from did.base import Config, ConfigError
from did.stats import StatsGroup, EmptyStatsGroup

# Self reference and file path to this module
PLUGINS = sys.modules[__name__]
PLUGINS_PATH = os.path.dirname(PLUGINS.__file__)

FAILED_PLUGINS = []

def load():
    """ Check available plugins and attempt to import them """
    # Code is based on beaker-client's command.py script
    plugins = []
    for filename in os.listdir(PLUGINS_PATH):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        if not os.path.isfile(os.path.join(PLUGINS_PATH, filename)):
            continue
        plugin = filename[:-3]
        if plugin in FAILED_PLUGINS:
            # Skip loading plugins that already failed before
            continue
        try:
            __import__(PLUGINS.__name__, {}, {}, [plugin])
            plugins.append(plugin)
            log.debug("Successfully imported {0} plugin".format(plugin))
        except (ImportError, SyntaxError) as error:
            log.warn("Failed to import {0} plugin ({1})".format(plugin, error))
            FAILED_PLUGINS.append(plugin)
    return plugins


def detect():
    """
    Detect available plugins and return enabled/configured stats

    Yields tuples of the form (section, statsgroup) sorted by the
    default StatsGroup order which maybe overriden in the config
    file. The 'section' is the name of the configuration section
    as well as the option used to enable those particular stats.
    """
    # Detect classes inherited from StatsGroup and return them sorted
    stats = []
    for plugin in load():
        module = getattr(PLUGINS, plugin)
        for object_name in dir(module):
            statsgroup = getattr(module, object_name)
            # Filter out anything except for StatsGroup descendants
            if (not isinstance(statsgroup, (type, types.ClassType))
                    or not issubclass(statsgroup, StatsGroup)
                    or statsgroup is StatsGroup
                    or statsgroup is EmptyStatsGroup):
                continue
            # Search config for sections with type matching the plugin,
            # use order provided there or class default otherwise
            for section in Config().sections(kind=plugin):
                try:
                    order = int(Config().item(section, "order"))
                except ConfigError:
                    order = statsgroup.order
                except ValueError:
                    log.warn("Invalid {0} stats order: '{1}'".format(
                        section, Config().item(section, "order")))
                    order = statsgroup.order
                stats.append((section, statsgroup, order))
                log.info("Found {0}, an instance of {1}, order {2}".format(
                    section, statsgroup.__name__, order))
                # Custom stats are handled with a single instance
                if statsgroup.__name__ == "CustomStats":
                    break
    for section, statsgroup, _ in sorted(stats, key=lambda x: x[2]):
        yield section, statsgroup
