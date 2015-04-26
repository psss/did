#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals, absolute_import


def test_SnippetRepo():
    # simple test that import works
    from status_report.snippetrepo import SnippetsRepo
    assert SnippetsRepo


def test_SnippetRepoSQLAlchemy():
    # simple test that import works
    from status_report.snippetrepo import SnippetsRepoSQLAlchemy
    assert SnippetsRepoSQLAlchemy


def test_Snippet():
    # simple test that import works
    from status_report.snippetrepo import Snippet
    assert Snippet
