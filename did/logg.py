# coding: utf-8
# @ Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals, absolute_import

import getpass
import os
from os.path import expanduser
import re
from subprocess import call
import tempfile

import did.base
from did.utils import log

try:
    import git
except ImportError:
    log.warn('GitPython not installed!')
    git = None

""" Logg and save idid activity stats with ease. """

"""
Overview
--------
``idid`` logg's can be stored in

 * plain text file (txt; DEFAULT)
 * git commits repo
  - target (topic) are branches
  - loggs are commits
  - can be 'cloned' and shared
"""

DT_ISO_FMT = "%Y-%m-%dT%H:%M:%S %z"
DT_GIT_FMT = "%Y-%m-%dT%H:%M:%S"

# Regex's
URI_RE = re.compile('([\w]*)://(.*)')

# only git backend supported; not sure why, but I think
# we might want to extend to support other 'backends' somehow
SUPPORTED_BACKENDS = ['txt']
if git:
    # only enable git backend if PythonGit is installed
    SUPPORTED_BACKENDS += ['git']

USER = getpass.getuser()
DEFAULT_ENGINE_DIR = expanduser('~/.did/loggs')
# TODO: Consider if we should resolve 'user' rather based on config email?
DEFAULT_ENGINE_PATH = '{0}/did-{1}.txt'.format(DEFAULT_ENGINE_DIR, USER)
DEFAULT_ENGINE_URI = 'txt://{0}'.format(DEFAULT_ENGINE_PATH)
# TODO: Consider if we should resolve 'user' rather based on config email?
LOGG_CONFIG_KEY = 'logg'

DEFAULT_GIT_ENGINE_PATH = '{0}/did-{1}.git'.format(DEFAULT_ENGINE_DIR, USER)
DEFAULT_GIT_ENGINE_URI = 'git://{0}'.format(DEFAULT_GIT_ENGINE_PATH)

COMMENT_RE = re.compile('^#')

LOGG_EDITOR = os.environ.get('EDITOR', 'vim')
# explain to the user that they are in a did git message editor
DEFAULT_LOGG_RECORD = """


# Please enter a did logg for the activities you completed on [{date}].
# Lines starting with '#' will be ignored, and an empty message
# aborts the commit.
#
# Saving idid logg to [{target}] branch
#
# Summary line must be
# * no more than 50c
# * separated from the body with a empty-line
"""


"""
# EXAMPLE CLI USAGE

    idid yesterday joy "@psss merged all my PRs! #did #FTW"

# EXAMPLE MODULE USAGE

    >>> from did import logg
    >>> l = logg.GitLogg()
    >>> l.logg_record('joy', '@psss merged all my pull requests!', 'yesterday')

# EXAMPLE CONFIG

    [general]
    email = "Chris Ward" <cward@redhat.com>

    [logg]
    engine = git
    strict = False  # default; allow use of unconfigured topic branches
    #gpg = 1C725D56  # use gpg to sign commits

    [joy]
    type = logg
    desc = Joy of the Day

    [tools]
    type = logg
    desc = My Tools
    engine = txt://~/.did/loggs/tools.txt # customize storage path


Logg Record can for example contain (for later parsing)::

 * any arbitrary text
 * @mention's to reference another user
 * #tags to include additional reference to shared theme or topic

With ``GitLogg`` backend it is also possible to save multiline logg messages.
eg::

    idid joy --   # launch $EDITOR

    Summary (50c max), with body separated by \n

    This is the detailed version of the did logg message that
    describes in more detail what actually happened...
"""

# FIXME: invidual but related dids on a single line separated by semi-colon


class LoggFactory(type):
    """ Detect the type of backend based on the engine uri and
        return the backend expected class automatically
    """
    def __call__(cls, config=None):
        _config = cls._load_config(config)
        engine = _config.get('engine')
        log.debug('LoggFactory loading [{0}]...'.format(engine))
        backend, path = cls._parse_engine(engine)
        cls = GitLogg if backend == 'git' else Logg
        log.debug(' ... Loading Backend Class: {0}'.format(cls))
        _type = type.__call__(cls, config)
        return _type


class Logg(object):
    """ did logg backend class for storing did messages """
    __metaclass__ = LoggFactory
    _config = None
    backeng = None
    config = None
    engine = None
    logg_repo = None
    path = None
    record = None
    since = None
    target = None
    until = None

    def __init__(self, config=None):
        # convert invlalid null values ('', [], False) to None
        # load the raw base config so we can parse through it later
        # to get individual logg target branch configs
        self._config = did.base.Config(config or None)
        self.config = self._load_config(self._config)
        # use the default engine if not specified
        self.engine = self.config.get('engine')
        # sets self.engine
        self.backend, self.path = self._parse_engine(self.engine)

    @staticmethod
    def _load_config(config=None):
        # get a config file, the default or the one passed in
        config = did.base.get_config(config)
        try:
            config = dict(config.section(LOGG_CONFIG_KEY))
        except did.base.ConfigFileError as err:
            log.warn("Error while loading config: [{0}]".format(err))
            # Don't panic yet if the section doesn't exist ...
            # maybe we don't actually need it ...
            config = {}
        return config

    @staticmethod
    def _parse_engine(engine):
        """ Parse the engine uri to determine where to store loggs """
        # default to storing as txt logg
        # NOTE: for testing purposes, make sure to always override
        # DEFAULT_ENGINE_URI users running tests to add test loggs accidently
        engine = (engine or 'txt').strip()
        try:
            backend, path = URI_RE.match(engine).groups()
        except (AttributeError, TypeError):
            # AttributeError if we don't have a match; None.groups() is invalid
            # Not sure now what might trigger TypeError, tbh...
            if engine == 'txt':
                log.info('Using default TXT engine store path [{0}]'.format(
                    DEFAULT_ENGINE_PATH))
                backend = 'txt'
                path = DEFAULT_ENGINE_PATH
            elif engine == 'git':
                log.info('Using default GIT engine store path [{0}]'.format(
                    DEFAULT_GIT_ENGINE_PATH))
                backend = 'git'
                path = DEFAULT_GIT_ENGINE_PATH
            else:
                raise TypeError('Invalid uri: {0}'.format(engine))

        # ENGINE CHECK
        # At this time, we only support git as a backend
        if backend not in SUPPORTED_BACKENDS:
            raise NotImplementedError(
                "Logg supports only {0} for now.".format(SUPPORTED_BACKENDS))
        log.debug('Found engine: {0}'.format(engine))

        # create path for engine store if not already available
        _dir = os.path.dirname(path)
        _exists = os.path.exists(_dir)
        if not _exists:
            log.warn(' Created logg storage path [{0}]'.format(_dir))
            os.makedirs(_dir)
        elif not os.path.isdir(_dir):
            raise RuntimeError('Engine store path exists but it is not a dir!')

        return backend, path

    def logg_record(self, target, record, date=None):
        if not (target and record):
            raise RuntimeError(
                "target [{0}] and record [{1}] must be defined".format(
                    target, record))
        # we want to store dates in txt as YYYY-MM-DD which is default
        # formate for Date() objects
        date = str(did.base.Date(date or did.base.TODAY))

        # If the user config has strict = true user must 'enable' the branch
        # targets they want to accept loggs for by adding them to the config
        # FIXME: filter only 'logg' type plugin config sections?
        if target not in self._config.sections(kind='logg'):
            log.warn("Target branch [{0}] is not configured!".format(target))
            strict = self.config.get('strict') or False
            if bool(strict):
                raise did.base.ConfigError(
                    'Target ({0}) not tracked; add to config'.format(target))

        self._target = target = target.decode('utf-8').strip()
        self._record = record = record.decode('utf-8').strip()
        # default format YYYY-MM-DD
        log.debug('Saving did Logg("{0}", "{1}", "{2}")'.format(
            target, record, date))
        result = self._logg_record(target, record, date)
        result = result.strip()
        log.info('SUCCESS: \n{0}'.format(result))
        return result

    def _logg_record(self, target, record, date):
        # self.path contains the path part of the engine uri
        mode = 'a' if os.path.exists(self.path) else 'w'
        with open(self.path, mode) as stdout:
            result = '{0} {1} [{2}]\n'.format(date, record, target)
            stdout.write(result)
        return result


class GitLogg(Logg):

    MAX_WIDTH = 50  # raise RuntimeError if logg record > MAX_WIDTH

    """ did logg backend to save loggs to a git repo """

    def __init__(self, *args, **kwargs):
        super(GitLogg, self).__init__(*args, **kwargs)
        # cache the logg_repo in the instance
        self._load_repo()

    def _logg_record(self, target, record, date):
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

        # record should respect MAX_WIDTH option in config
        k_record = len(record)
        # make sure we get an int out the config...
        max_width = int(self.config.get('max_width', self.MAX_WIDTH))
        log.debug('Record `max_width` is {0}'.format(max_width))
        if k_record > max_width:
            raise RuntimeError("Record is too bigger than {0}; got {1}. "
                               "Try using just --".format(max_width, k_record))

        try:
            result = self._commit(target, record, date, sync=True)
        except KeyboardInterrupt as err:
            log.error('Error encountered during git commit: {0}'.format(err))
            raise SystemExit('\n\n')
        return result

    # FIXME: sync; sync_tx == remotee, remotees
    def _commit(self, target, record, date, sync=None):
        # date shouldn't be None
        # make sure we actually have a repo to commit to
        # self._load_repo()    # sets self.logg_repo
        # checkout the target branch, but make sure to return to
        # pre-commit state after completion (clean-up) ...
        # always sync/backup/merge commits for 'full-audit' "master" branch
        current = self.logg_repo.active_branch
        sync_to = 'master' if sync else None
        # Make absolutely sure we have a git 1.8+ compatible date format!
        date = did.base.Date(date, fmt=DT_GIT_FMT)
        kwargs = dict(date=date, allow_empty=True)
        # Build dict for sending as args to the git commend
        # -- or null says we want to open our editor to edit the commit msg
        if record in ['--', None]:
            # inspired by: http://stackoverflow.com/a/6309753/1289080
            with tempfile.NamedTemporaryFile(suffix=".tmp") as _tmp:
                _n = _tmp.name
                description = DEFAULT_LOGG_RECORD.format(**dict(target=target,
                                                                date=date))
                _tmp.write(description)
                _tmp.flush()
                call([LOGG_EDITOR, _n])
                record = [x.strip(' ') for x in open(_n).readlines() if x]
                record = [x for x in record if not COMMENT_RE.match(x)]
                k_lines = len(record)
                if k_lines > 1:
                    # complain that we expect the SUMMARY / MSG BODY form
                    if not record[1] == '\n':
                        raise RuntimeError(
                            'Invalid format. Usage:\nSUMMARY\n\nMESSAGE...')
                record = ''.join(record).strip()
                if not record:
                    raise SystemExit('Empty Logg. Aborting.')
        # Include the record in the git command too
        kwargs['m'] = record

        # FIXME: add documentation to describe this config option
        # if gpg key is defined in .config [logg], git will attempt to
        # sign the commits with the provided key
        gpg_sign = self.config.get('gpg', None)
        if gpg_sign:
            kwargs['gpg_sign'] = gpg_sign

        try:
            log.debug("Checking out branch: {0}".format(target))
            self._checkout_branch(target)
            r = self.logg_repo.git.commit(**kwargs)

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

    def _checkout_branch(self, branch=None):
        branch = branch or 'master'
        # Try to create the target branch
        try:
            self.logg_repo.git.checkout(branch, b=True)
        except git.GitCommandError:
            # branch already exists, so check it out
            self.logg_repo.git.checkout(branch)

    def _load_repo(self):
        """ Load git repo using GitPython """
        if not self.logg_repo:
            if os.path.exists(self.path):
                log.info('Found git repo [{0}]'.format(self.path))
                self.logg_repo = git.Repo(self.path)
            else:
                # create the repo if it doesn't already exist
                self.logg_repo = git.Repo.init(path=self.path, mkdir=True)
                log.info('Created git repo [{0}]'.format(self.path))
                record = "New did repo added by {0}".format(USER)
                # FIXME: calling tests via make Makefile with git hook
                # creates some sort of environmental difference that
                # breaks this! I've tried debugging for several hours
                # with no luck.
                # `make smoke` works but git commit which calls hooks/pre-commit
                # which calls `make smoke`... fails
                self.logg_repo.index.commit(record)
