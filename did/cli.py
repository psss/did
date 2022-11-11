# coding: utf-8

"""
Command line interface for did

This module takes care of processing command line options and
running the main loop which gathers all individual stats.
"""

import argparse
import re
import sys

from dateutil.relativedelta import relativedelta as delta

import did.base
from did import utils
from did.stats import UserStats
from did.utils import log

USAGE = """
did [this|last] [week|month|quarter|year] [options]

What did you do last week, month, year?

Comfortably gather status report data for given week, month,
quarter, year or selected date range. By default all available
stats for this week are reported.
""".strip()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Options
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Options(object):
    """ Command line options parser """

    def __init__(self, arguments=None):
        """ Prepare the parser. """
        self.parser = argparse.ArgumentParser(usage=USAGE)
        self._prepare_arguments(arguments)
        self.opt = self.arg = None

        # Enable debugging output (even before options are parsed)
        if "--debug" in self.arguments:
            log.setLevel(utils.LOG_DEBUG)
        # Use a simple test config if smoke test requested
        if "--test" in self.arguments:
            did.base.Config(did.base.TEST_CONFIG)

        # Get the default output width from the config (if available)
        try:
            width = did.base.Config().width
        except did.base.ConfigFileError:
            width = did.base.MAX_WIDTH

        # Time & user selection
        group = self.parser.add_argument_group("Select")
        group.add_argument(
            "--email", dest="emails", default=[], action="append",
            help="User email address(es)")
        group.add_argument(
            "--since",
            help="Start date in the YYYY-MM-DD format")
        group.add_argument(
            "--until",
            help="End date in the YYYY-MM-DD format")

        # Create sample stats and include all stats objects options
        log.debug("Loading Sample Stats group to build Options")
        self.sample_stats = UserStats()
        self.sample_stats.add_option(self.parser)
        log.info("Default command line: did {0}".format(" ".join(
            [f'--{stat.option}' for stat in self.sample_stats.stats])))

        # Formating options
        group = self.parser.add_argument_group("Format")
        group.add_argument(
            "--format", default="text",
            help="Output style, possible values: text (default) or wiki")
        group.add_argument(
            "--width", default=width, type=int,
            help="Maximum width of the report output (default: %(default)s)")
        group.add_argument(
            "--brief", action="store_true",
            help="Show brief summary only, do not list individual items")
        group.add_argument(
            "--verbose", action="store_true",
            help="Include more details (like modified git directories)")

        # Other options
        group = self.parser.add_argument_group("Utils")
        group.add_argument(
            "--config",
            metavar="FILE",
            help="Use alternate configuration file (default: 'config')")
        group.add_argument(
            "--total", action="store_true",
            help="Append total stats after listing individual users")
        group.add_argument(
            "--merge", action="store_true",
            help="Merge stats of all users into a single report")
        group.add_argument(
            "--debug", action="store_true",
            help="Turn on debugging output, do not catch exceptions")
        group.add_argument(
            "--test", action="store_true",
            help="Run a simple smoke test against the github server")

    def _prepare_arguments(self, arguments):
        """ Prepare arguments (both direct and from command line) """
        # Split arguments if given as string
        if arguments is not None:
            if isinstance(arguments, str):
                self.arguments = arguments.split()
            else:
                self.arguments = arguments
        # Otherwise process command line arguments
        else:
            self.arguments = sys.argv[1:]

    def parse(self):
        """ Parse the options. """
        # Run the parser
        opt, arg = self.parser.parse_known_args(self.arguments)
        self.opt = opt
        self.arg = arg
        self.check()

        # Enable --all if no particular stat or group selected
        opt.all = not any([
            getattr(opt, stat.dest) or getattr(opt, group.dest)
            for group in self.sample_stats.stats
            for stat in group.stats])

        # Time period handling
        if opt.since is None and opt.until is None:
            opt.since, opt.until, period = did.base.Date.period(arg)
        else:
            opt.since = did.base.Date(opt.since or "1993-01-01")
            opt.until = did.base.Date(opt.until or "today")
            # Make the 'until' limit inclusive
            opt.until.date += delta(days=1)
            period = "given date range"

        # Validate the date range
        if not opt.since.date < opt.until.date:
            raise RuntimeError(
                "Invalid date range ({0} to {1})".format(
                    opt.since, opt.until.date - delta(days=1)))
        header = "Status report for {0} ({1} to {2}).".format(
            period, opt.since, opt.until.date - delta(days=1))

        # Finito
        log.debug("Gathered options:")
        log.debug('options = {0}'.format(opt))
        return opt, header

    def check(self):
        """ Perform additional check for given options """
        keywords = [
            'today', 'yesterday', 'friday',
            'this', 'last',
            'week', 'month', 'quarter', 'year']
        for argument in self.arg:
            if argument not in keywords:
                raise did.base.OptionError(
                    "Invalid argument: '{0}'".format(argument))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main(arguments=None):
    """
    Parse options, gather stats and show the results

    Takes optional parameter ``arguments`` which can be either
    command line string or list of options. This is very useful
    for testing purposes. Function returns a tuple of the form::

        ([user_stats], team_stats)

    with the list of all gathered stats objects.
    """
    try:
        # Load standard and custom plugins
        utils.load_components("did.plugins", continue_on_error=True)
        try:
            custom_plugins = did.base.Config().plugins
            if custom_plugins:
                custom_plugins = [
                    plugin.strip() for plugin in utils.split(custom_plugins)]
                utils.load_components(*custom_plugins, continue_on_error=True)
        except did.base.ConfigFileError:
            pass

        # Parse options, initialize gathered stats
        options, header = Options(arguments).parse()
        gathered_stats = []

        # Check for user email addresses (command line or config)
        emails = options.emails or did.base.Config().email
        emails = utils.split(emails, separator=re.compile(r"\s*,\s*"))
        users = [did.base.User(email=email) for email in emails]

        # Print header and prepare team stats object for data merging
        print(header)
        team_stats = UserStats(options=options)
        if options.merge:
            utils.header("Total Report", did.base.Config().separator_width, did.base.Config().separator)
            utils.item("Users: {0}".format(len(users)), options=options)

        # Check individual user stats
        for user in users:
            if options.merge:
                utils.item(user, 1, options=options)
            else:
                utils.header(user, did.base.Config().separator_width, did.base.Config().separator)
            user_stats = UserStats(user=user, options=options)
            user_stats.check()
            team_stats.merge(user_stats)
            gathered_stats.append(user_stats)

        # Display merged team report
        if options.merge or options.total:
            if options.total:
                utils.header("Total Report", did.base.Config().separator_width, did.base.Config().separator)
            team_stats.show()

        # Return all gathered stats objects
        return gathered_stats, team_stats

    except did.base.ConfigFileError:
        utils.info("Create at least a minimum config file {0}:\n{1}".format(
            did.base.Config.path(), did.base.Config.example().strip()))
        raise
