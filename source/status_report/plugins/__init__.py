"""
Plugins for status-report

Modules in this direcotry are searched for available stats. Each
plugin should contain a single class inheriting from StatsGroup.
Stats from this group will be included in the report if enabled in
user config. Name of the plugin should match config section type.
Attribute 'order' defines the default order in the final report.
"""

import os
import sys
import types

from status_report.base import StatsGroup, EmptyStatsGroup
from status_report.utils import Config, ConfigError, log

# Self reference and file path to this module
PLUGINS = sys.modules[__name__]
PLUGINS_PATH = os.path.dirname(PLUGINS.__file__)

def detect():
    """
    Detect available plugins and return enabled/configured stats

    Yields tuples of the form (section, statsgroup) sorted by the
    default StatsGroup order which maybe overriden in the config
    file. The 'section' is the name of the configuration section
    as well as the option used to enable those particular stats.
    """

    # Detect available plugins and attempt to import them
    # (Code is based on beaker-client's command.py script)
    plugins = []
    for filename in os.listdir(PLUGINS_PATH):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        if not os.path.isfile(os.path.join(PLUGINS_PATH, filename)):
            continue
        plugin = filename[:-3]
        try:
            __import__(PLUGINS.__name__, {}, {}, [plugin])
            plugins.append(plugin)
            log.debug("Successfully imported {0} plugin".format(plugin))
        except (ImportError, SyntaxError), error:
            log.warn("Failed to import {0} plugin ({1})".format(plugin, error))

    # Detect classes inherited from StatsGroup and return them sorted
    stats = []
    for plugin in plugins:
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
