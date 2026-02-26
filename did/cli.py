"""
Command line interface for did

This module takes care of processing command line options and
running the main loop which gathers all individual stats.
"""

import argparse
import re
import sys
from typing import Optional, Union

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

class Options:
    """ Command line options parser """

    def __init__(self, arguments: Union[None, str, list[str]] = None):
        """ Prepare the parser. """
        self.parser = argparse.ArgumentParser(usage=USAGE)
        self._prepare_arguments(arguments)
        self.opt: argparse.Namespace
        self.arg: Optional[list[str]]

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
            width = utils.MAX_WIDTH

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
        log.info("Default command line: did %s",
                 (" ".join([f'--{stat.option}' for stat in self.sample_stats.stats])))

        # Formatting options
        group = self.parser.add_argument_group("Format")
        group.add_argument(
            "--format", default="text", choices=["text", "markdown", "wiki"],
            help="Output style, default: text")
        group.add_argument(
            "--width", default=width, type=int,
            help="Maximum width of the report output (default: %(default)s)")
        group.add_argument(
            "--brief", action="store_true",
            help="Show brief summary only, do not list individual items")
        group.add_argument(
            "--verbose", action="store_true",
            help="Include more details (like modified git directories)")
        group.add_argument(
            "--full-message", action="store_true",
            help="Show full commit messages, PR descriptions, and issue bodies")

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

    def _prepare_arguments(self, arguments: Union[None, str, list[str]]) -> None:
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

    def parse(self) -> tuple[argparse.Namespace, str]:
        """ Parse the options. """
        # Run the parser
        opt: argparse.Namespace
        arg: list[str]
        opt, arg = self.parser.parse_known_args(self.arguments)
        self.opt = opt
        self.arg = arg
        self.check()

        # Enable --all if no particular stat or group selected
        opt.all = not any(
            getattr(opt, stat.dest) or getattr(opt, group.dest)
            for group in self.sample_stats.stats
            for stat in group.stats)

        # Time period handling
        if opt.since is None and opt.until is None:
            opt.since, opt.until, period = did.base.Date.period(arg)
        else:
            if self.arg:
                raise did.base.OptionError(
                    f'Can\'t use --since or --until with \'{" ".join(self.arg)}\''
                    )
            opt.since = did.base.Date(opt.since or "1993-01-01")
            opt.until = did.base.Date(opt.until or "today")
            # Make the 'until' limit inclusive
            opt.until.date += delta(days=1)
            period = "given date range"

        if opt.since is None or opt.until is None:
            raise RuntimeError("Date range not properly initialized")
        # Validate the date range
        if opt.since.date >= opt.until.date:
            raise RuntimeError(
                f"Invalid date range ({opt.since} to {opt.until.date - delta(days=1)})")

        header = (
            f"Status report for {period} ({opt.since} "
            f"to {opt.until.date - delta(days=1)})"
            )
        if opt.format == "markdown":
            # In markdown the first line must be a header
            # using alternate syntax allowing to use did's
            # output in commit messages as well
            header = f"{header}\n{'=' * len(header)}"
        else:
            # In markdown no trailing punctuation is allowed in headings
            header = f"{header}."

        # Finito
        log.debug("Gathered options:")
        log.debug('options = %s', opt)
        return opt, header

    def check(self) -> None:
        """ Perform additional check for given options """
        keywords = [
            'today', 'yesterday', 'monday', 'tuesday', 'wednesday', 'thursday',
            'friday', 'saturday', 'sunday',
            'this', 'last',
            'week', 'month', 'quarter', 'year']
        if self.arg is None:
            raise RuntimeError("Programming error: call `parse` before `check`")
        for argument in self.arg:
            if argument not in keywords:
                raise did.base.OptionError(f"Invalid argument: '{argument}'")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main(arguments: Union[None, str, list[str]] = None
         ) -> tuple[list[UserStats], UserStats]:
    """
    Parse options, gather stats and show the results

    Takes optional parameter ``arguments`` which can be either
    command line string or list of options. This is very useful
    for testing purposes. Function returns a tuple of the form::

        ([user_stats], team_stats)

    with the list of all gathered stats objects.
    """
    config = None
    try:
        config = did.base.Config()
    except did.base.ConfigFileError:
        utils.info(
            f"Create at least a minimum config file {did.base.Config.path()}:"
            f"\n{did.base.Config.example().strip()}")
        raise

    # Load standard and custom plugins
    utils.load_components("did.plugins", continue_on_error=True)
    if config:
        custom_plugins = config.plugins
        if custom_plugins:
            custom_plugins_list = [
                plugin.strip()
                for plugin in utils.split(custom_plugins)]
            utils.load_components(*custom_plugins_list, continue_on_error=True)

    # Parse options, initialize gathered stats
    options, header = Options(arguments).parse()
    gathered_stats = []

    # at this point if `--test` was used, Config() is filled.
    config = did.base.Config()

    # Check for user email addresses (command line or config)
    emails = options.emails or config.email
    emails = utils.split(emails, separator=re.compile(r"\s*,\s*"))
    users = [did.base.User(email=email) for email in emails]

    # Print header and prepare team stats object for data merging
    print(header)
    team_stats = UserStats(options=options)
    if options.merge:
        utils.header(
            "Total Report",
            separator=config.separator,
            separator_width=config.separator_width)
        utils.item(f"Users: {len(users)}", options=options)

    # Check individual user stats
    for user in users:
        if options.merge:
            utils.item(str(user), 1, options=options)
        else:
            utils.header(
                str(user),
                separator=config.separator,
                separator_width=config.separator_width)
        user_stats = UserStats(user=user, options=options)
        user_stats.check()
        # Show the results stats (unless merging)
        if not options.merge:
            user_stats.show()
        team_stats.merge(user_stats)
        gathered_stats.append(user_stats)

    # Display merged team report
    if options.merge or options.total:
        if options.total:
            utils.header(
                "Total Report",
                separator=config.separator,
                separator_width=config.separator_width)
        team_stats.show()

    # Return all gathered stats objects
    return gathered_stats, team_stats
