#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals, absolute_import

import os
from did import utils


class Mock(object):
    pass


script_path = os.path.dirname(os.path.realpath(__file__))
# go all the way to the git repo root (2 levels up)
git_path = os.path.realpath('{0}/../../'.format(script_path))

CONFIG = """
[general]
email = "Chris Ward" <cward@redhat.com>
[test_header]
type = git
did = {0}
""".format(git_path)

options = Mock()
options.since = '2015-04-01'
options.until = '2015-04-24'
options.verbose = True

user_cward = Mock()
user_cward.login = 'cward'
user_psplicha = Mock()
user_psplicha.login = 'psplicha'

parent = Mock()
parent.options = options
parent.user = user_cward


def test_GitRepo():
    utils.Config(CONFIG)
    from did.plugins.git import GitRepo
    assert GitRepo

    repo = GitRepo(path=git_path)
    commits = repo.commits(user=user_cward, options=options)
    assert len(commits) > 0

    repo = GitRepo(path='bad path')
    try:
        repo.commits(user=user_cward, options=options)
    except utils.ReportError:
        pass
    else:
        raise RuntimeError("expected a failure")


def test_GitCommits():
    utils.Config(CONFIG)
    from did.plugins.git import GitCommits
    assert GitCommits

    stats = GitCommits(option='test_header',
                       name='Working on topic',
                       parent=parent,
                       path=git_path)
    stats.user = user_cward
    stats.fetch()
    assert len(stats.stats) > 0

    stats.user = user_psplicha
    stats.fetch()
    assert len(stats.stats) > 0


def test_GitStats():
    utils.Config(CONFIG)
    from did.plugins.git import GitStats
    assert GitStats

    stats = GitStats(option='test_header',
                     name='Working on topic',
                     parent=parent)

    stats.user = user_cward
    stats.fetch()
