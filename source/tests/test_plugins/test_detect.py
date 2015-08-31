#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals, absolute_import


def test_load():
    from status_report.plugins import load
    assert load


def test_detect():
    from status_report.plugins import detect
    assert detect
