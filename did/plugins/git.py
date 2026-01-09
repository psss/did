"""
Git commits

Config example::

    [tools]
    type = git
    did = ~/git/did
    edd = ~/git/edd
    fmf = ~/git/fmf

    [tests]
    type = git
    fedora = ~/tests/fedora/*
    rhel = ~/tests/rhel/*

Note that using an ``*`` you can enable multiple git repositories at
once. Non git directories from the expansion are silently ignored.
"""

import os
import re
import subprocess

import did.base
from did.stats import Stats, StatsGroup
from did.utils import item, log, pretty

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Git Repository
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class GitRepo():
    """ Git repository investigator """
    # pylint: disable=too-few-public-methods

    def __init__(self, path):
        """ Initialize the path. """
        self.path = path

    # pylint: disable=too-many-branches
    def commits(self, user, options):
        """ List commits for given user. """
        # Prepare the command
        command = f"git log --all --author={user.login}".split()
        command.append(f"--since='{options.since} 00:00:00'")
        command.append(f"--until='{options.until} 00:00:00'")
        if getattr(options, 'full_message', False):
            # Full message mode: show hash and complete commit body
            # Use NULL character as separator between commits
            command.append("--format=format:%h - %B%x00")
        elif options.verbose:
            command.append("--name-only")
            # Need an extra new line to separate merge commits otherwise
            # they are squeezed together without an empty line between
            command.append("--format=format:%n%h - %s")
        else:
            command.append("--format=format:%h - %s")
        log.info("Checking commits in %s", self.path)
        log.details(pretty(command))

        # Get the commit messages
        try:
            with subprocess.Popen(
                    command,
                    cwd=self.path,
                    encoding='utf-8',
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                    ) as process:
                output, errors = process.communicate()
                output = output.strip()
                log.debug("git log output:")
                log.debug(output)
                if process.returncode != 0:
                    log.debug(errors.strip())
                    log.warning("Unable to check commits in '%s'", self.path)
                    return []
        except OSError as error:
            log.debug(error)
            raise did.base.ReportError(f"Unable to access git repo '{self.path}'")

        if not output:
            return []

        # Full message mode: commits separated by NULL character
        if getattr(options, 'full_message', False):
            commits = []
            for commit in output.split("\x00"):
                commit = commit.strip()
                if not commit:
                    continue
                # first line is "hash - subject" then body
                lines = commit.split("\n")
                if len(lines) == 1:
                    commits.append(lines[0])
                else:
                    # Indent body lines with 8 spaces for proper display
                    formatted = lines[0]
                    for line in lines[1:]:
                        if line.strip():
                            formatted += f"\n        {line}"
                    commits.append(formatted)
            return commits

        # Single commit per line in non-verbose mode
        if not options.verbose:
            return output.split("\n")

        # In verbose mode commits separated by two empty lines
        commits = []
        for commit in re.split("\n\n+", output):
            lines = commit.split("\n")

            # Use a single line if no files changed (e.g. merges)
            if len(lines) == 1:
                commits.append(lines[0])

            # Show the first directory with modified files
            # FIXME: But why just the first one? Shouldn't we show
            # all? Or at least more? With a maximum limit?
            else:
                directory = re.sub("/[^/]+$", "", lines[1])
                commits.append(f"{lines[0]}\n        * {directory}")
        return commits


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Git Commits
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitCommits(Stats):
    """ Git commits """

    def __init__(self, option, name=None, parent=None, path=None):
        super().__init__(option=option, name=name, parent=parent)
        self.path = path
        self.repo = GitRepo(self.path)

    def fetch(self):
        self.stats = self.repo.commits(self.user, self.options)

    def header(self):
        """ Show summary header. """
        # A bit different header for git stats: Work on xxx: x commit(s)
        # FIXME: better handling for `commit` plural
        item(
            f'{self.name}: {len(self.stats)} '
            f'commit{"" if len(self.stats) == 1 else "s"}',
            level=0, options=self.options)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Git Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GitStats(StatsGroup):
    """ Git stats group """

    # Default order
    order = 300

    def __init__(self, option, name=None, parent=None, user=None):
        name = f"Work on {option}"
        StatsGroup.__init__(self, option, name, parent, user)
        for repo, path in did.base.Config().section(option):
            path = os.path.expanduser(path)
            if path.endswith('/*'):
                try:
                    directories = os.listdir(path[:-1])
                except OSError as error:
                    log.error(error)
                    raise did.base.ConfigError(
                        f"Invalid path in the [{option}] section")
                for repo_dir in sorted(directories):
                    repo_path = path.replace('*', repo_dir)
                    # Check directories only
                    if not os.path.isdir(repo_path):
                        continue
                    # Silently ignore non-git directories
                    if not os.path.exists(os.path.join(repo_path, ".git")):
                        log.debug("Skipping non-git directory '%s'.", repo_path)
                        continue
                    self.stats.append(
                        GitCommits(
                            option=f"{repo}-{repo_dir}",
                            parent=self, path=repo_path,
                            name=f"Work on {repo}/{repo_dir}"
                            )
                        )
            else:
                self.stats.append(GitCommits(
                    option=f"{option}-{repo}", parent=self, path=path,
                    name=f"Work on {repo}"))
