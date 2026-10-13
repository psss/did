# coding: utf-8
""" Tests for the git plugin """

import logging
import os
import subprocess

from _pytest.logging import LogCaptureFixture

import did.cli
import did.utils

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Prepare interval and config file with real path to our git repo
INTERVAL = "--since 2015-09-07 --until 2015-09-11"
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
GIT_PATH = os.path.realpath(f'{SCRIPT_PATH}/../../')
CONFIG = """
[general]
email = "Petr Splichal" <psplicha@redhat.com>

[tools]
type = git
did = {0}
"""

# Config limiting the search to selected branches
CONFIG_BRANCHES = """
[general]
email = "Petr Splichal" <psplicha@redhat.com>

[tools]
type = git
branches_to_check = main devel
did = {0}
"""

# Config limiting the search to a single branch
CONFIG_SINGLE_BRANCH = """
[general]
email = "Petr Splichal" <psplicha@redhat.com>

[tools]
type = git
branches_to_check = main
did = {0}
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Smoke
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_git_smoke():
    """ Git smoke """
    did.base.Config(CONFIG.format(GIT_PATH))
    did.cli.main(INTERVAL)


def test_git_verbosity():
    """ Brief git stats """
    did.base.Config(CONFIG.format(GIT_PATH))
    did.cli.main(f"{INTERVAL} --brief")
    did.cli.main(f"{INTERVAL} --verbose")


def test_git_format():
    """ Wiki format """
    did.base.Config(CONFIG.format(GIT_PATH))
    did.cli.main(f"{INTERVAL} --format text")
    did.cli.main(f"{INTERVAL} --format wiki")


def test_git_team():
    """ Team report """
    emails = "--email psplicha@redhat.com,cward@redhat.com"
    did.base.Config(CONFIG.format(GIT_PATH))
    did.cli.main(f"{INTERVAL} {emails}")
    did.cli.main(f"{INTERVAL} {emails} --total")
    did.cli.main(f"{INTERVAL} {emails} --merge")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Content
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_git_regular():
    """ Simple git stats """
    did.base.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    assert any(
        "8a725af - Simplify git plugin tests" in stat
        for stat in stats)


def test_git_verbose():
    """ Verbose git stats """
    did.base.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main(f"{INTERVAL} --verbose")[0][0].stats[0].stats[0].stats
    assert any("tests/plugins" in stat for stat in stats)


def test_git_nothing():
    """ No stats found """
    did.base.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main("--until 2015-01-01")[0][0].stats[0].stats[0].stats
    assert stats == []


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Branches to check
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_git_branches_default():
    """ All branches are searched by default """
    did.base.Config(CONFIG.format(GIT_PATH))
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0]
    assert stats.repo.branches is None


def test_git_branches_selected():
    """ The search can be limited to selected branches """
    did.base.Config(CONFIG_BRANCHES.format(GIT_PATH))
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0]
    assert stats.repo.branches == ["main", "devel"]
    # The 'branches_to_check' option must not be treated as a repository
    assert len(did.cli.main(INTERVAL)[0][0].stats[0].stats) == 1


def test_git_branch_matching_file_name(tmp_path):
    """ Branch name matching a file name must not cause a failure """
    # Create a repo with a branch and a file sharing the same name so
    # that 'git log main' would otherwise be an ambiguous argument
    repo = tmp_path / "repo"
    repo.mkdir()
    date = "2015-09-08 12:00:00"
    env = {**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    for args in (
            ["init", "-q", "-b", "main"],
            ["config", "user.email", "psplicha@redhat.com"],
            ["config", "user.name", "Petr Splichal"]):
        subprocess.run(["git", *args], cwd=repo, check=True)
    (repo / "main").write_text("content\n")
    subprocess.run(["git", "add", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Add the main file"],
        cwd=repo, check=True, env=env)
    # The commit must be found despite the branch/file name collision
    did.base.Config(CONFIG_SINGLE_BRANCH.format(repo))
    stats = did.cli.main(INTERVAL)[0][0].stats[0].stats[0].stats
    assert any("Add the main file" in stat for stat in stats)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Errors
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_git_invalid():
    """ Invalid git repo """
    did.base.Config(CONFIG.format("/tmp"))
    try:
        did.cli.main(INTERVAL)
    except SystemExit as exc:
        raise RuntimeError("Expected warning only") from exc


def test_git_non_existent(caplog: LogCaptureFixture):
    """ Non-existent git repo """
    did.base.Config(CONFIG.format("i-do-not-exist"))
    with caplog.at_level(logging.ERROR):
        did.cli.main(INTERVAL)
        assert "Unable to access git repo" in caplog.text
