# coding: utf-8

"""
Command line interface for did

This module takes care of processing command line options and
running the main loop which gathers all individual stats.

Usage, for saving did logg's::

    idid chores 'Cleaned my inbox #ftw'
    idid proj_x 'Drafted Project X Charter'
    idid yesterday proj_x 'Fixed the leaky pipe'
    idid 2015-05-05T09:00:00 confs 'Attended PyCon CZ in Brno'
    idid 'something amazing today! #lifeisgreat'

If a target Logg topic branch is not specificed, 'unsorted' will be used.

Usage, for reporting did logg's::

    did
    did today
    did last week --logg

"""

from __future__ import unicode_literals, absolute_import

import re
import sys
import argparse
import kerberos
from dateutil.relativedelta import relativedelta as delta

import did.base
import did.utils as utils
from did.utils import log
from did.stats import UserStats
from did.logg import Logg, DT_ISO_FMT

VALID_LONG_DT_KEYWORDS = "this last".split()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Options
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DID_USAGE = "did [today|DATE|...] [[this|last] [week|month|...]] [options]"
IDID_USAGE = "idid [today|DATE|...] [topic] 'Logg record' [options]"


class Options(object):
    """ Command line options parser """

    arguments = None
    config = None

    def __init__(self, arguments=None):
        """ Prepare the shared [i]did argument parser """
        self.parser = argparse.ArgumentParser(usage=DID_USAGE)
        # if we don't pass args, we can assume we're calling this via CLI
        # so grab the args from sys.argv instead
        self.arguments = arguments or sys.argv[1:]
        log.debug(' ... arguments? {0}'.format(self.arguments))

        # Enable debugging output (even before options are parsed)
        if "--debug" in self.arguments:
            log.setLevel(utils.LOG_DEBUG)
        #  Turn off everything except errors, including warnings
        if "--quiet" in self.arguments:
            log.setLevel(utils.LOG_ERROR)

        # Head / Parent parser (shared)
        # Add Debug option
        self.parser.add_argument(
            "--debug", action="store_true",
            help="Turn on debugging output, do not catch exceptions")
        # Add quiet, which overrides debug if both are issued
        self.parser.add_argument(
            "--quiet", action="store_true",
            help="Turn off all logging except errors; catch exceptions")

        # Time & user selection
        group = self.parser.add_argument_group("Select")
        group.add_argument(
            "--email", dest="emails", default=[], action="append",
            help="User email address(es)")
        group.add_argument("--since", help="Start date in YYYY-MM-DD format")
        group.add_argument("--until", help="End date in YYYY-MM-DD format")

    def parse(self, arguments=None):
        """ Parse the shared [i]did arguments """
        arguments = self.arguments or arguments
        # FIXME: prep/normalize arguments in __init__
        # Split arguments if given as string and run the parser
        if isinstance(arguments, basestring):
            arguments = utils.split(arguments)

        # run the wrapped argparser command to gather user set arg values
        # FROM: https://docs.python.org/3/library/argparse.html
        # Sometimes a script may only parse a few of the command-line
        # arguments, passing the remaining arguments on to another script or
        # program.  In these cases, the parse_known_args() method can be
        # useful. It works much like parse_args() except that it does not
        # produce an error when extra arguments are present. Instead, it
        # returns a two item tuple containing the populated namespace and
        # the list of remaining argument strings.
        opts, _arguments = self.parser.parse_known_args(arguments)

        # if we're passing arguments in as a string we might get \n's or null
        # strings '' that we want to be sure to ignore
        _arguments = filter(
            lambda x: x if x else None, [_.strip() for _ in _arguments if _])

        # Now let the subclass parse the remaining special opts that
        # weren't consumed by default argparser
        opts = self._parse(opts, _arguments)
        return opts


class ReportOptions(Options):
    """ ``did`` command line arguments parser """

    def __init__(self, arguments=None):
        """ Customize argument parser for ``did``"""
        super(ReportOptions, self).__init__(arguments=arguments)

        self.parser.add_argument(
            "--all", action="store_true", help="Get all available stats")

        # Formating options
        group = self.parser.add_argument_group("Format")
        group.add_argument(
            "--format", default="text",
            help="Output style, possible values: text (default) or wiki")
        group.add_argument(
            "--width", default=did.base.MAX_WIDTH, type=int,
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

    def parse(self, *args, **kwargs):
        """ Load plugin arguments before parsing CLI arguments """
        # Create sample stats and include all stats objects options

        # NOTE: Only those plugins which have a value configured in the user's
        # config file will be loaded.

        log.debug("Loading Sample Stats group to build Options")
        self.sample_stats = UserStats()
        self.sample_stats.add_option(self.parser)
        return super(ReportOptions, self).parse(*args, **kwargs)

    def _parse(self, opts, args):
        """ Perform additional check for ``did`` command arguments """
        # did [today|yesterday|this...] [week|month|...]
        assert isinstance(args, list)

        # return all stats if one or more are specified explicitly
        opts.all = not any([
            getattr(opts, stat.dest) or getattr(opts, group.dest)
            for group in self.sample_stats.stats
            for stat in group.stats])

        # Time period handling
        if opts.since is None and opts.until is None:
            opts.since, opts.until, opts.period = did.base.Date.period(args)
        else:
            opts.since = did.base.Date(opts.since or "1993-01-01")
            opts.until = did.base.Date(opts.until or "today")
            # Make the 'until' limit inclusive
            opts.until.date += delta(days=1)
            opts.period = "given date range"

        # Validate the date range
        if not opts.since.date < opts.until.date:
            raise RuntimeError(
                "Invalid date range ({0} to {1})".format(
                    opts.since, opts.until.date - delta(days=1)))

        # This check needs to be run after ALL plugins have been loaded
        # and their custom args have been added to the parser
        # parser.parse_known_args() has been run; otherwise parse_known_args
        # doesn't remove the plugin args from the arguments list since it
        # doesn't know anything about them at the time it runs and thinks
        # they aren't actually real argparser args, since in reality
        # they aren't, since they haven't been added at the time this
        # _parse() check is run currently.
        keywords = "today yesterday this last week month quarter year".split()
        err = [1 if arg not in keywords else 0 for arg in args]
        if any(err):
            raise did.base.OptionError(
                "Invalid argument: '{0}'".format(args[err.index(1)]))

        # Finito
        log.debug("Gathered options:")
        log.debug('options = {0}'.format(opts))
        return opts


class LoggOptions(Options):
    """ ``idid`` command line arguments parser """

    logg = None

    def __init__(self, arguments=None):
        """ Customize argument parser for ``idid``"""
        super(LoggOptions, self).__init__(arguments=arguments)
        self.parser.usage = IDID_USAGE

    def _parse_date(self, dt, fmt=None):
        """ Try to convert a given value to a did.base.Date() instance """
        try:
            # test if it's not a datelike instance ...
            _dt = did.base.Date(dt, fmt=fmt)
        except did.base.OptionError:
            # nope, not a datelike instance
            _dt = None
        return _dt

    def _parse(self, opts, args):
        """ Perform additional check for ``idid`` command arguments """
        k_args = len(args)
        _dt = opts.date = None
        logg = opts.logg = None
        target = opts.target = None

        log.debug(' ... got [{0}] args'.format(k_args))
        if k_args == 0:
            # launch the editor to save a message into 'unsorted' branch
            # FIXME: 'unsorted' should be configurable as 'default branch'
            log.warn('Target branch is not defined, using "unsorted"')
            target, logg = 'unsorted', '--'

        elif k_args == 1:
            # NOTE: two different usage patterns can be expected here
            # 1) did target   # launch EDITOR for logg in target topic
            # 2) did 'logg record'  # save under default branch 'unsorted'
            # if we have a value that's got more than one word in it, we
            # assume it's a logg (B), otherwise (A)
            arg = args.pop()
            k_words = len(arg.split())
            # variant A); user wants to launch the editor
            # variany B); user wants to save record to 'unsorted' branch
            # default to an unspecified, unsorted target branch since
            # target not specified
            target, logg = (arg, '--') if k_words == 1 else ('unsorted', arg)
            if target == 'unsorted':
                log.warn('Target branch is not defined, using "unsorted"')

        elif k_args == 2:
            # variants:
            # 1) did [datetime] 'message'
            # 2) did [datetime] target  # launch editor
            # 3) did target logg
            # 4) did unquoted logg  # NOT VALID
            # 5) did last week  # NOT VALID
            _one = args[0]
            _two = args[1]

            if _one in VALID_LONG_DT_KEYWORDS:
                # scenario 5), pass the entire string to date
                raise RuntimeError(
                    "Invalid date use. Got: [{0} {1}]".format(_one, _two))

            # try to parse a date from the value
            _dt = self._parse_date(_one, DT_ISO_FMT)

            # scenario 1) or 2), ambiguouos ... could be target or logg msg
            # assume 2) by default, so... 1) is invalid
            # scenario 3) or 4), ambiguous ... could be target or
            # logg msg assume 3) by default, so... 4) is invalid
            target, logg = (_two, '--') if _dt else (_one, _two)

        elif k_args >= 3:
            # variants:
            # 1) did [datetime] target 'message'
            # 2) did [datetime] unquoted logg  # NOT VALID
            # 3) did target unquoted logg
            _one = args[0]
            _two = args[1]
            _three = ' '.join(args[2:])

            if _one in VALID_LONG_DT_KEYWORDS:
                # scenario 5), pass the entire string to date
                raise RuntimeError(
                    "Invalid date use. Got: [{0} {1}]".format(_one, _two))

            # try to parse a date from the value
            _dt = self._parse_date(_one, DT_ISO_FMT)

            # scenario 1) or 2), ambiguouos ... could be target or logg msg
            # assume 1) by default, so... 2) is invalid
            __combo = _two + ' ' + _three
            target, logg = (_two, _three) if _dt else (_one, __combo)

        opts.date = _dt or did.base.Date('today', fmt=DT_ISO_FMT)
        opts.target = target
        opts.logg = logg
        log.debug(' Found Date: {0}'.format(_dt))
        log.debug(' Found Target: {0}'.format(target))
        log.debug(' Found Logg: {0}'.format(logg))
        return opts


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _run_logg(arguments, config):
    # running idid logg
    options = LoggOptions(arguments=arguments).parse()
    logg = Logg(config)
    r = logg.logg_record(options.target, options.logg, options.date)
    # We're not doing everything else did does... Finito
    return r


def _run_report(arguments, config):
    # We have a did report command
    gathered_stats = []

    # parse the cli arguments and gather options
    options = ReportOptions(arguments=arguments).parse()

    # Reporting record stats
    header = "Status report for {0} ({1} to {2}).".format(
        options.period, options.since,
        (options.until.date - delta(days=1)).date())

    # Check for user email addresses (command line or config)
    # Make sure to load the config that's passed in, if one is...
    emails = options.emails or config.email
    emails = utils.split(emails, separator=re.compile(r"\s*,\s*"))
    users = [did.base.User(email=email) for email in emails]

    # Print header and prepare team stats object for data merging
    utils.eprint(header)
    team_stats = UserStats(options=options)
    if options.merge:
        utils.header("Total Report")
        utils.item("Users: {0}".format(len(users)), options=options)

    # Check individual user stats
    for user in users:
        if options.merge:
            utils.item(user, 1, options=options)
        else:
            utils.header(user)

        user_stats = UserStats(user=user, options=options)
        user_stats.check()
        team_stats.merge(user_stats)
        gathered_stats.append(user_stats)

    # Display merged team report
    if options.merge or options.total:
        if options.total:
            utils.header("Total Report")
        team_stats.show()

    # Return all gathered stats objects
    return gathered_stats, team_stats


# FIXME: UPDATE API DOCS FOR MAIN()
def main(arguments=None, config=None, is_logg=None):
    """
    Parse arguments for ``did`` and ``idid`` commands.

    Run ``idid`` by setting is_logg = True. Otherwise, main
    will attempt to generate a ``did`` report.

    Pass optional parameter ``arguments`` as either command line
    string or list of options. This is mainly useful for testing.

    ``config`` can be passed in as a string to access user defined
    values for important variables manually. This is mainly useful
    for testing.

    If being run for ``did`` reporting, main() returns a tuple of the form::

        ([user_stats], team_stats)

    If being run for ``idid`` logg save, main() returns the saved
    logg string.

    """
    # FIXME: shouldn't these try:excepts be catching
    # only the ONE function that's expected to possibly raise the
    # excepted exceptions?

    config = did.base.set_config(config)

    try:
        # Parse options, initialize gathered stats
        if is_logg:
            return _run_logg(arguments, config)
        else:
            return _run_report(arguments, config)

    # FIXME catch at the level where kerberos is actually known to be used?
    except kerberos.GSSError as error:
        log.debug(error)
        raise did.base.ConfigError(
            "Kerberos authentication failed. Try kinit.")
