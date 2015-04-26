#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals, absolute_import


def test_import():
    # simple test that import works
    from status_report.plugins import snippet
    assert snippet


def test_Snippets():
    from status_report.plugins.snippet import Snippets
    assert Snippets


def test_SnippetStats():
    from status_report.plugins.snippet import SnippetStats
    assert SnippetStats
