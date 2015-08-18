#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Comfortably generate reports - Git """

import os
import re
import subprocess
from status_report.base import Stats, StatsGroup
from status_report.utils import Config, item, log, pretty


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
        log.info(u"Checking commits in {0}".format(self.path))
        log.debug(pretty(command))

        # Get the commit messages
        try:
            process = subprocess.Popen(
                command, cwd=self.path,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as error:
            log.warn("Unable to access git repo in {0}".format(self.path))
            raise
        output, errors = process.communicate()
        log.debug("git log output:")
        log.debug(output)
        if process.returncode == 0:
            if not output:
                return []
            else:
                if not options.verbose:
                    return unicode(output, "utf8").split("\n")
                commits = []
                for commit in unicode(output, "utf8").split("\n\n"):
                    summary = commit.split("\n")[0]
                    directory = re.sub("/[^/]+$", "", commit.split("\n")[1])
                    commits.append("{0}\n{1}* {2}".format(
                        summary, 8 * " ", directory))
                return commits
        else:
            log.warn("Unable to check commits in {0}".format(self.path))
            log.warn(errors.strip())
            return []


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Git Commits
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class GitCommits(Stats):
    """ Git commits """
    def __init__(self, option, name=None, parent=None, path=None,
                 options=None):
        super(GitCommits, self).__init__(option=option, name=name,
                                         parent=parent, options=options)
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

    def fetch(self):
        # FIXME: path should be pushed in and used from kwarg
        # not pull from config here...
        repos = Config().section(self.option)
        log.debug('Found {0} repo paths'.format(len(repos)))
        log.debug(repos)
        for repo, path in repos:
            if path.endswith('/*'):
                for repo_dir in sorted(os.listdir(path[:-1])):
                    repo_path = path.replace('*', repo_dir)
                    option = "{0}-{1}".format(repo, repo_dir)
                    name = "Work on {0}/{1}".format(repo, repo_dir)
                    commits = GitCommits(option=option, parent=self,
                                         path=repo_path, name=name)
                    commits.fetch()
                    self.stats.append(commits)
            else:
                name = "Work on {0}".format(repo)
                commits = GitCommits(option=repo, parent=self,
                                     path=path, name=name)
                commits.fetch()
                self.stats.append(commits)
