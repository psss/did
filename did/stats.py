# coding: utf-8

""" Stats & StatsGroup, the core of the data gathering """

import xmlrpc.client

import did.base
from did import utils
from did.utils import log


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Stats(object):
    """ General statistics """
    _name = None
    _error = None
    _enabled = None
    option = None
    dest = None
    parent = None
    stats = None

    def __init__(
            self, option, name=None, parent=None, user=None, options=None):
        """ Set the name, indent level and initialize data.  """
        self.option = option.replace(" ", "-")
        self.dest = self.option.replace("-", "_")
        self._name = name
        self.parent = parent
        self.stats = []
        # Save user and options (get it directly or from parent)
        self.options = options or getattr(self.parent, 'options', None)
        if user is None and self.parent is not None:
            self.user = self.parent.user
        else:
            self.user = user
        log.debug(
            'Loading {0} Stats instance for {1}'.format(option, self.user))

    @property
    def name(self):
        """ Use the first line of docs string unless name set. """
        if self._name:
            return self._name
        return [
            line.strip() for line in self.__doc__.split("\n")
            if line.strip()][0]

    def add_option(self, group):
        """ Add option for self to the parser group object. """
        group.add_argument(
            "--{0}".format(self.option), action="store_true", help=self.name)

    def enabled(self):
        """ Check whether we're enabled (or if parent is). """
        # Cache into ._enabled
        if self._enabled is None:
            if self.parent is not None and self.parent.enabled():
                self._enabled = True
            else:
                # Default to Enabled if not otherwise disabled
                self._enabled = getattr(self.options, self.dest, True)
        return self._enabled

    def fetch(self):
        """ Fetch the stats (to be implemented by respective class). """
        raise NotImplementedError()

    def check(self):
        """ Check the stats if enabled. """
        if not self.enabled():
            return
        try:
            self.fetch()
        except (xmlrpc.client.Fault, did.base.ConfigError) as error:
            log.error(error)
            self._error = True
            # Raise the exception if debugging
            if not self.options or self.options.debug:
                raise
        # Show the results stats (unless merging)
        if self.options and not self.options.merge:
            self.show()

    def header(self):
        """ Show summary header. """
        # Show question mark instead of count when errors encountered
        count = "? (error encountered)" if self._error else len(self.stats)
        utils.item("{0}: {1}".format(self.name, count), options=self.options)

    def show(self):
        """ Display indented statistics. """
        if not self._error and not self.stats:
            return
        self.header()
        for stat in self.stats:
            utils.item(stat, level=1, options=self.options)

    def merge(self, other):
        """ Merge another stats. """
        for other_stat in other.stats:
            if other_stat not in self.stats:
                self.stats.append(other_stat)
        if other._error:
            self._error = True


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class StatsGroupPlugin(type):
    registry = {}
    ignore = set([
            "StatsGroupPlugin",
            "StatsGroup",
            "EmptyStatsGroup",
            "UserStats",
        ])

    def __init__(cls, name, bases, attrs):
        if name in StatsGroupPlugin.ignore:
            return

        plugin_name = cls.__module__.split(".")[-1]
        registry = StatsGroupPlugin.registry

        if plugin_name in registry:
            orig = registry[plugin_name]
            log.warn("%s overriding %s" % (cls.__module__, orig.__module__))

        registry[plugin_name] = cls


class StatsGroup(Stats, metaclass=StatsGroupPlugin):
    """ Stats group """

    # Default order
    order = 500

    def add_option(self, parser):
        """ Add option group and all children options. """

        group = parser.add_argument_group(self.name)
        for stat in self.stats:
            stat.add_option(group)

        group.add_argument(
            "--{0}".format(self.option), action="store_true", help="All above")

    def check(self):
        """ Check all children stats. """
        for stat in self.stats:
            stat.check()

    def show(self):
        """ List all children stats. """
        for stat in self.stats:
            stat.show()

    def merge(self, other):
        """ Merge all children stats. """
        for this, other in zip(self.stats, other.stats):
            this.merge(other)

    def fetch(self):
        """ Stats groups do not fetch anything """
        pass


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  User Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UserStats(StatsGroup):
    """ User statistics in one place """

    def __init__(self, user=None, options=None, config=None):
        """ Initialize stats objects. """
        super(UserStats, self).__init__(
            option="all", user=user, options=options)
        config = config or did.base.Config()
        try:
            self.stats = self.configured_plugins(config)
        except did.base.ConfigFileError as error:
            # Missing config file is OK if building options (--help).
            # Otherwise raise the expection to suggest config example.
            if options is None:
                log.debug(error)
                log.debug("This is OK for now as we're just building options.")
            else:
                raise

    def configured_plugins(self, config):
        """ Create a StatsGroup instance for each configured plugin """
        results = []
        items_created = False
        for section in config.sections():
            if section == "general":
                continue

            data = dict(config.section(section, skip=set()))
            type_ = data.get("type")

            # All 'items' stats are gathered under a single group
            if type_ == 'items':
                if items_created:
                    continue
                else:
                    items_created = True

            if not type_:
                msg = "Plugin type not defined in section '{0}'."
                raise did.base.ConfigError(msg.format(section))

            if type_ not in StatsGroupPlugin.registry:
                raise did.base.ConfigError(
                    "Invalid plugin type '{0}' in section '{1}'.".format(
                        type_, section))

            user = self.user.clone(section) if self.user else None
            statsgroup = StatsGroupPlugin.registry[type_]
            obj = statsgroup(option=section, parent=self, user=user)
            # Override default order if requested
            if 'order' in data:
                try:
                    obj.order = int(data['order'])
                except ValueError:
                    raise did.base.GeneralError(
                        f"Invalid order '{data['order']}' "
                        f"in the '{section}' section.")
            results.append(obj)
        return sorted(results, key=lambda x: x.order)

    def add_option(self, parser):
        """ Add options for each stats group. """
        for stat in self.stats:
            stat.add_option(parser)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Header & Footer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class EmptyStats(Stats):
    """ Custom stats group for header & footer """
    def __init__(self, option, name=None, parent=None, user=None):
        Stats.__init__(self, option, name, parent, user)

    def show(self):
        """ Name only for empty stats """
        utils.item(self.name, options=self.options)

    def fetch(self):
        """ Nothing to do for empty stats """
        pass


class EmptyStatsGroup(StatsGroup):
    """ Header & Footer stats group """
    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        for opt, name in sorted(did.base.Config().section(option)):
            self.stats.append(
                EmptyStats(option + "-" + opt, name, parent=self))
