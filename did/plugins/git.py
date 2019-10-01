# coding: utf-8
"""
Git commits

Config example::

    [tools]
    type = git
    did = /home/psss/git/did
    edd = /home/psss/git/edd
    fmf = /home/psss/git/fmf

    [tests]
    type = git
    fedora = /home/psss/tests/fedora/*
    rhel = /home/psss/tests/rhel/*

Note that using an ``*`` you can enable multiple git repositories at
once. Non git directories from the expansion are silently ignored.
"""

import os
import re
import subprocess

import did.base
from did.utils import item, log, pretty
from did.stats import Stats, StatsGroup


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Git Repository
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitRepo(object):
    """ Git repository investigator """
    def __init__(self, path):
        """ Initialize the path. """
        self.path = path

    def commits(self, user, options):
        """ List commits for given user. """
        # Prepare the command
        command = "git log --all --author={0}".format(user.login).split()
        command.append("--format=format:%h - %s")
        command.append("--since='{0} 00:00:00'".format(options.since))
        command.append("--until='{0} 00:00:00'".format(options.until))
        if options.verbose:
            command.append("--name-only")
        log.info("Checking commits in {0}".format(self.path))
        log.details(pretty(command))

        # Get the commit messages
        try:
            process = subprocess.Popen(
                command, cwd=self.path, encoding='utf-8',
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as error:
            log.debug(error)
            raise did.base.ReportError(
                "Unable to access git repo '{0}'".format(self.path))
        output, errors = process.communicate()
        log.debug("git log output:")
        log.debug(output)
        if process.returncode == 0:
            if not output:
                return []
            else:
                if not options.verbose:
                    return output.split("\n")
                commits = []
                for commit in output.split("\n\n"):
                    summary = commit.split("\n")[0]
                    directory = re.sub("/[^/]+$", "", commit.split("\n")[1])
                    commits.append("{0}\n{1}* {2}".format(
                        summary, 8 * " ", directory))
                return commits
        else:
            log.debug(errors.strip())
            log.warn("Unable to check commits in '{0}'".format(self.path))
            return []


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Git Commits
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitCommits(Stats):
    """ Git commits """
    def __init__(self, option, name=None, parent=None, path=None):
        super(GitCommits, self).__init__(
            option=option, name=name, parent=parent)
        self.path = path
        self.repo = GitRepo(self.path)

    def fetch(self):
        self.stats = self.repo.commits(self.user, self.options)

    def header(self):
        """ Show summary header. """
        # A bit different header for git stats: Work on xxx: x commit(s)
        item(
            "{0}: {1} commit{2}".format(
                self.name, len(self.stats),
                "" if len(self.stats) == 1 else "s"),
            level=0, options=self.options)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Git Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitStats(StatsGroup):
    """ Git stats group """

    # Default order
    order = 300

    def __init__(self, option, name=None, parent=None, user=None):
        name = "Work on {0}".format(option)
        StatsGroup.__init__(self, option, name, parent, user)
        for repo, path in did.base.Config().section(option):
            if path.endswith('/*'):
                try:
                    directories = os.listdir(path[:-1])
                except OSError as error:
                    log.error(error)
                    raise did.base.ConfigError(
                        "Invalid path in the [{0}] section".format(option))
                for repo_dir in sorted(directories):
                    repo_path = path.replace('*', repo_dir)
                    # Check directories only
                    if not os.path.isdir(repo_path):
                        continue
                    # Silently ignore non-git directories
                    if not os.path.exists(os.path.join(repo_path, ".git")):
                        log.debug("Skipping non-git directory '{0}'.".format(
                            repo_path))
                        continue
                    self.stats.append(GitCommits(
                        option="{0}-{1}".format(repo, repo_dir),
                        parent=self, path=repo_path,
                        name="Work on {0}/{1}".format(repo, repo_dir)))
            else:
                self.stats.append(GitCommits(
                    option=option + "-" + repo, parent=self, path=path,
                    name="Work on {0}".format(repo)))
