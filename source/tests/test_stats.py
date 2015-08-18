#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals, absolute_import


def test_Stats():
    # simple test that import works
    from status_report.base import Stats
    assert Stats


def test_StatsGroup():
    # simple test that import works
    from status_report.base import StatsGroup
    assert StatsGroup


def test_UserStats():
    # simple test that import works
    from status_report.base import UserStats
    assert UserStats


def test_EmptyStats():
    # simple test that import works
    from status_report.base import EmptyStats
    assert EmptyStats


def test_EmptyStatsGroup():
    # simple test that import works
    from status_report.base import EmptyStatsGroup
    assert EmptyStatsGroup
