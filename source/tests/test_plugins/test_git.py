#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals, absolute_import

import os


class Mock(object):
    pass


script_pth = os.path.dirname(os.path.realpath(__file__))
# go all the way to the git repo root (3 levels up)
git_pth = os.path.realpath('{0}/../../../'.format(script_pth))

options = Mock()
options.since = '2015-04-01'
options.until = '2015-04-24'
options.verbose = True

user_cward = Mock()
user_cward.login = 'cward'
user_psplicha = Mock()
user_psplicha.login = 'psplicha'

with open(os.path.expanduser('~/.status-report'), 'w') as f:
    f.write('[general]\nemail = "Chris Ward" <cward@redhat.com>\n')
    f.write('\n[test_header]\ntype = git\nstatus-report = {0}'.format(git_pth))


def test_GitRepo():
    from status_report.plugins.git import GitRepo
    assert GitRepo

    repo = GitRepo(path=git_pth)
    commits = repo.commits(user=user_cward, options=options)
    assert len(commits) > 0

    repo = GitRepo(path='bad path')
    try:
        repo.commits(user=user_cward, options=options)
    except OSError:
        pass
    else:
        raise RuntimeError("expected a failure")


def test_GitCommits():
    from status_report.plugins.git import GitCommits
    assert GitCommits

    stats = GitCommits(option='test_header',
                       name='Working on topic',
                       parent=None,
                       path=git_pth,
                       options=options)
    stats.user = user_cward
    stats.fetch()
    assert len(stats.stats) > 0

    stats.user = user_psplicha
    stats.fetch()
    assert len(stats.stats) > 0


def test_GitStats():
    from status_report.plugins.git import GitStats
    assert GitStats

    stats = GitStats(option='test_header',
                     name='Working on topic',
                     parent=None,
                     options=options)

    stats.user = user_cward
    stats.fetch()
