# coding: utf-8
# @ Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals, absolute_import

import ConfigParser
import getpass
import os
from os.path import expanduser
import re

import git

import did.base
from did.utils import log

""" Log and save your did's """

"""
EXPERIMENTAL
based on psss's https://github.com/psss/did/issues/38#issuecomment-144431647

data store is git repo
Branch is 'target log'
Commits are 'logs'
Commiter and date is present from the git log by default
 - possible to ammend

store's on (eg) github are easily 'cloneable' (aka, subscribable)

"""

# only git backend supported; not sure why, but I think
# we might want to extend to support other 'backends' somehow
SUPPORTED_BACKENDS = ['git']
URI_RE = re.compile('([\w]*)://(.*)')
USER = getpass.getuser()
DEFAULT_ENGINE_DIR = expanduser('~/.did/loggs')
# TODO: Consider if we should resolve 'user' rather based on config email?
DEFAULT_ENGINE_PATH = '{0}/did-{1}.git'.format(DEFAULT_ENGINE_DIR, USER)
DEFAULT_ENGINE_URI = 'git://{0}'.format(DEFAULT_ENGINE_PATH)
LOGG_CONFIG_KEY = 'logg'

"""
# EXAMPLE USAGE

    did logg joy yesterday "@psss merged all my PRs! #did #FTW"

# EXAMPLE CONFIG

    [general]
    email = "Chris Ward" <cward@redhat.com>

    [work]
    type = logg
    joy = Joy of the Week
    tools = Working on Tooling


Logg Record can contain

 * any arbitrary text
 * invidual but related dids can be on a single line separated by semi-colon's
 * @mention's to reference another user
 * #tags to include additional reference to shared theme or topic

"""

# FIXME: Add 'bio' 'about me' README.rst to the repo
# cv

# FIXME: add --expand to enable launcing an editor and taking a longer
# commit message with deeper explanation of the SUBJ


class Logg(object):
    """ Git did log class for saving did messages locally to git repo """
    _args = None
    config = None
    date = None
    engine = None
    logg_repo = None
    record = None
    target = None

    def __init__(self, args, config=None):
        self._args = args or []
        self._load_config(config)  # sets self.config
        self._parse_engine()  # sets self.engine
        self._parse_logg()   # sets self.target, self.record, self.date
        self._load_repo()    # sets self.logg_repo

    def logg_record(self, target=None, record=None, date=None):
        """
        # %> did logg work 2015-01-01 '... bla bla #tag @mention ...'
        # results in a logg entry in the 'work' datastore for $DATE (by user)

        # author_date = '2015-01-01T01:01:01'
        # record = 'Did something AMAZING! [#id] #did'

        # info about specifying a specific date for the committ
        # http://stackoverflow.com/a/3898842/1289080
        # Each commit has two dates: the author date and the committer date.

        # commit the record and update the commit date to
        # r.git.commit(m=record, date=author_date, allow_empty=True)
        """
        # FIXME: take emails from config (extracted in CLI already)
        # FIXME: extract out the possible dates and other tokens
        # FIXME: check that we're using the write dates here...
        # FIXME: check if it isn't a duplicate... of the previous
        # and abort usless it's forced
        #
        # git date option needs HH:MM:SS +0000 specified too or it will assume
        # current time values instead of 00:00:00
        #
        # When passing this I get a commit on
        #  Date: Thu Jan 1 09:32:32 2015 +0100
        # when just passing utcnow() i get
        #  Date: Sun Oct 11 08:31:51 2015 +0200
        # according to my clock (CET; +0200) it's Oct 11 10:33:...

        target = target or self.target
        record = record or self.record
        date = date or self.date
        # normalized date format; git expects iso datetime; -micro (.%f)
        iso = '%Y-%m-%d %H:%M:%S %z'
        date = unicode(did.base.Date(date, fmt=iso))
        log.info('Saving did Logg("{0}", "{1}")'.format(target, record))
        result = self._commit(target, record, date, sync=True)
        log.info('SUCCESS: \n{0}'.format(result))

    @property
    def _args_len(self):
        return len(self._args or [])

    def _commit(self, target, record, date, sync=None):
        # checkout the target branch, but make sure to return to
        # pre-commit state after completion (clean-up) ...

        # always sync/backup/merge commits for 'full-audit' "master" branch
        current = self.logg_repo.active_branch
        sync_to = 'master' if sync else None
        try:
            log.debug("Checking out branch: {0}".format(target))
            self._checkout_branch(target)
            r = self.logg_repo.git.commit(m=record, date=date, allow_empty=True)
            if sync_to:
                # sync/backup branch (master)
                log.info(' ... also syncing to: {0}'.format(sync_to))
                record = '{0} [{1}]'.format(record, target)
                result_sync = self._commit(sync_to, record, date, sync=False)
                log.info(' ... ... {0}'.format(result_sync))
        finally:
            if self.logg_repo.active_branch != current:
                log.debug(
                    " ... cleaning up (git checkout {0}...".format(current))
                self._checkout_branch(current)
        return r

    def _check_config(self):
        pass

    def _check_logg(self):
        """ Perform additional check for given options for LOG command """
        if not self._args:
            raise ValueError("args is empty; try passing something in?")
        if self._args_len not in (3, 4):
            raise RuntimeError(
                "logg cmd invalid; usage: `logg target [YYYY-MM-DD] 'bla bla'`")

    def _checkout_branch(self, branch=None):
        branch = branch or 'master'
        # Try to create the target branch
        try:
            self.logg_repo.git.checkout(branch, b=True)
        except git.GitCommandError:
            # branch already exists, so check it out
            self.logg_repo.git.checkout(branch)

    def _load_config(self, config=None):
        try:
            config = dict(did.base.Config(config).section(LOGG_CONFIG_KEY))
        except ConfigParser.NoSectionError:
            # Don't panic if the section doesn't exist; _check_config()
            # will check the state of config... maybe {} is OK?
            config = {}
        self.config = config
        self._check_config()

    def _load_repo(self):
        """ """
        if os.path.exists(self.path):
            log.info('FOUND {0}'.format(self.path))
            r = git.Repo(self.path)
        else:
            # create the repo if it doesn't already exist
            log.info('CREATED {0}'.format(self.path))
            r = git.Repo.init(path=self.path, mkdir=True)
            r.index.commit("New did repo added")
        # git checkout
        self.logg_repo = r

    def _parse_logg(self):
        """ Parse LOG command """
        self._check_logg()
        if self._args_len == 3:
            target, record = self._args[1:3]
            date = 'today'  # default
        else:
            assert self._args_len == 4
            target, date, record = self._args[1:4]
        self.target = target
        self.record = record.decode('utf-8')
        self.date = date

        # Require that the user explicitly 'enable' the branch targets
        # they want to accept loggs for
        if target not in self.config:
            raise did.base.ConfigError(
                'Target ({0}) not tracked; add to config'.format(target))

    def _parse_engine(self):
        """ """
        # use the default engine if not specified
        self.engine = self.config.get('engine') or DEFAULT_ENGINE_URI
        try:
            self.backend, self.path = URI_RE.match(self.engine).groups()
        except TypeError:
            # bad uri
            # uri = '{0}://{1}'.format(backend, path)
            raise TypeError('Invalid uri!')

        # ENGINE CHECK ()
        # At this time, we only support git as a backend
        if self.backend not in SUPPORTED_BACKENDS:
            raise NotImplementedError(
                "Logg supports only {0} for now.".format(SUPPORTED_BACKENDS))
