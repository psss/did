""" Stats & StatsGroup, the core of the data gathering """

from __future__ import annotations

import argparse
import re
import sys
import xmlrpc.client
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

import did.base
from did import utils
from did.utils import log

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Stats():
    """ General statistics """
    _name: str | None
    error: bool = False
    _enabled = None
    option: str
    dest: str
    user: Optional[did.base.User]
    parent: Optional[StatsGroup] = None

    def __init__(
            self, /,
            option: str,
            name: Optional[str] = None,
            parent: Optional[StatsGroup] = None,
            user: Optional[did.base.User] = None, *,
            options: Optional[argparse.Namespace] = None):
        """ Set the name, indent level and initialize data.  """
        self.option = option.replace(" ", "-")
        self.dest = self.option.replace("-", "_")
        self._name = name
        self.parent = parent
        self._stats: list[Any] = []
        # Save user and options (get it directly or from parent)
        self.options = options or getattr(self.parent, 'options', None)
        if user is None and self.parent is not None:
            self.user = self.parent.user
        else:
            self.user = user
        log.debug('Loading %s Stats instance for %s', option, self.user)

    @property
    def stats(self) -> list[Any]:
        """Stats list; subclasses may override this property."""
        return self._stats

    @stats.setter
    def stats(self, value: list[Any]) -> None:
        self._stats = value

    @property
    def name(self) -> str:
        """ Use the first line of docs string unless name set. """
        if self._name:
            return self._name
        return [
            line.strip() for line in str(self.__doc__).split("\n")
            if line.strip()][0]

    def add_option(self, parser: argparse.ArgumentParser) -> None:
        """ Add option for self to the parser group object. """
        parser.add_argument(f"--{self.option}", action="store_true", help=self.name)

    def enabled(self) -> bool:
        """ Check whether we're enabled (or if parent is). """
        # Cache into ._enabled
        if self._enabled is None:
            if self.parent is not None and self.parent.enabled():
                self._enabled = True
            else:
                # Default to Enabled if not otherwise disabled
                self._enabled = getattr(self.options, self.dest, True)
        return self._enabled

    def fetch(self) -> None:
        """ Fetch the stats (to be implemented by respective class). """
        raise NotImplementedError()

    def check(self) -> None:
        """ Check the stats if enabled. """
        if not self.enabled():
            return
        try:
            self.fetch()
        except (
                xmlrpc.client.Fault,
                did.base.ConfigError,
                ConnectionError
                ) as error:
            log.error(error)
            self.error = True
            # Raise the exception if debugging
            if not self.options or self.options.debug:
                raise

    def header(self) -> None:
        """ Show summary header. """
        # Show question mark instead of count when errors encountered
        count = "? (error encountered)" if self.error else len(self.stats)
        utils.item(f"{self.name}: {count}", options=self.options)

    def show(self) -> None:
        """ Display indented statistics. """
        if not self.error and not self.stats:
            return
        self.header()
        for stat in self.stats:
            utils.item(stat, level=1, options=self.options)

    def merge(self, other: Stats) -> None:
        """ Merge another stats. """
        for other_stat in other.stats:
            if other_stat not in self.stats:
                self.stats.append(other_stat)
        if other.error:
            self.error = True


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class StatsGroupPlugin(type):
    registry: dict[str, "StatsGroupPlugin"] = {}
    ignore = set([
        "StatsGroupPlugin",
        "StatsGroup",
        "EmptyStatsGroup",
        "UserStats",
        ])

    def __init__(cls, name: str, _bases: tuple[type, ...], _attrs: dict[str, Any]):
        if name in StatsGroupPlugin.ignore:
            return

        plugin_name = cls.__module__.rsplit(".", maxsplit=1)[-1]
        registry = StatsGroupPlugin.registry

        if plugin_name in registry:
            orig = registry[plugin_name]
            log.warning("%s overriding %s", cls.__module__, orig.__module__)

        registry[plugin_name] = cls


class StatsGroup(Stats, metaclass=StatsGroupPlugin):
    """ Stats group """

    # Default order
    order = 500

    def add_option(self, parser: argparse.ArgumentParser) -> None:
        """ Add option group and all children options. """

        group = parser.add_argument_group(self.name)
        for stat in self.stats:
            stat.add_option(group)

        group.add_argument(f"--{self.option}", action="store_true", help="All above")

    def check(self) -> None:
        """ Check all children stats. """
        with ThreadPoolExecutor() as executor:
            result_futures = []
            for stat in self.stats:
                result_futures.append(executor.submit(stat.check))
            for f in as_completed(result_futures):
                # Raise exceptions if raised within the executor.
                try:
                    f.result()
                except did.base.ReportError as error:
                    log.error("Skipping %s due to %s", f, error)
                    sys.stdout.flush()
                    sys.stderr.flush()

    def show(self) -> None:
        """ List all children stats. """
        for stat in self.stats:
            stat.show()

    def merge(self, other: Stats) -> None:
        """ Merge all children stats. """
        for this, other_stats in zip(self.stats, other.stats):
            this.merge(other_stats)

        self.error = any(stat.error for stat in self.stats)

    def fetch(self) -> None:
        """ Stats groups do not fetch anything """


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  User Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UserStats(StatsGroup):
    """ User statistics in one place """

    def __init__(self,
                 user: Optional[did.base.User] = None,
                 options: Optional[argparse.Namespace] = None,
                 config: Optional[did.base.Config] = None) -> None:
        """ Initialize stats objects. """
        super().__init__(option="all", user=user, options=options)
        config = config or did.base.Config()
        try:
            self.stats = self.configured_plugins(config)
        except did.base.ConfigFileError as error:
            # Missing config file is OK if building options (--help).
            # Otherwise raise the exception to suggest config example.
            if options is None:
                log.debug(error)
                log.debug("This is OK for now as we're just building options.")
            else:
                raise

    def configured_plugins(self, config: did.base.Config) -> list[StatsGroup]:
        """ Create a StatsGroup instance for each configured plugin """
        results: list[StatsGroup] = []
        for section in config.sections():
            if section == "general":
                continue

            data = dict(config.section(section, skip=()))
            type_ = data.get("type")

            if not type_:
                msg = "Plugin type not defined in section '{0}'."
                raise did.base.ConfigError(msg.format(section))

            # Some plugins (like public-inbox) need to have underscores
            # in their names to follow python modules conventions, but
            # it's more user-friendly to have dashes instead, so let's
            # replace all the dashes by underscores.
            type_ = type_.replace('-', '_')

            if type_ not in StatsGroupPlugin.registry:
                raise did.base.ConfigError(
                    f"Invalid plugin type '{type_}' in section '{section}'.")

            user = self.user.clone(section) if self.user else None
            statsgroup = StatsGroupPlugin.registry[type_]
            try:
                obj = statsgroup(option=section, parent=self, user=user)
                orig_order = obj.order
                # Override default order if requested
                if 'order' in data:
                    try:
                        obj.order = int(data['order'])
                    except ValueError as exc:
                        raise did.base.GeneralError(
                            f"Invalid order '{data['order']}' "
                            f"in the '{section}' section.") from exc
                if orig_order != obj.order:
                    log.debug("Reordered %s from %s to %s",
                              repr(obj), orig_order, obj.order)
                results.append(obj)
            except did.base.ReportError as re_err:
                log.error("Skipping section %s due to error: %s", section, re_err)
        return sorted(results, key=lambda x: x.order)

    def add_option(self, parser: argparse.ArgumentParser) -> None:
        """ Add options for each stats group. """
        for stat in self.stats:
            stat.add_option(parser)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Header & Footer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class EmptyStats(Stats):
    """ Custom stats group for header & footer """

    def __init__(self,
                 option: str,
                 name: Optional[str] = None,
                 parent: Optional[EmptyStatsGroup] = None,
                 user: Optional[did.base.User] = None):
        Stats.__init__(self, option, name, parent, user)

    def show(self) -> None:
        """ Name only for empty stats """
        # Convert escaped new lines into real new lines
        # (in order to support custom subitems for each item)
        item = re.sub(r"\\n", "\n", self.name)
        utils.item(item, options=self.options)

    def fetch(self) -> None:
        """ Nothing to do for empty stats """


class EmptyStatsGroup(StatsGroup):
    """ Header & Footer stats group """

    def __init__(self,
                 option: str,
                 name: Optional[str] = None,
                 parent: Optional[StatsGroup] = None,
                 user: Optional[did.base.User] = None) -> None:
        StatsGroup.__init__(self, option, name, parent, user)
        for opt, opt_name in sorted(did.base.Config().section(option)):
            self.stats.append(
                EmptyStats(f"{option}-{opt}", opt_name, parent=self))
