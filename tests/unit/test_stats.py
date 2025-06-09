# coding: utf-8

import did.stats


def test_stats_class_exists():
    assert did.stats.Stats


def test_statsgroup_class_exists():
    assert did.stats.StatsGroup


def test_userstats_class_exists():
    assert did.stats.UserStats


def test_emptystats_class_exists():
    assert did.stats.EmptyStats


def test_emptystatsgroup_class_exists():
    assert did.stats.EmptyStatsGroup
