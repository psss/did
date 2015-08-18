#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals, absolute_import


def test_get_plugins():
    from status_report.plugins import get_plugins
    assert get_plugins


def test_load_plugins():
    from status_report.plugins import load_plugins
    assert load_plugins


def test_detect():
    from status_report.plugins import detect
    assert detect
