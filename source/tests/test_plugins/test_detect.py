#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals, absolute_import


def test_load():
    from did.plugins import load
    assert load


def test_detect():
    from did.plugins import detect
    assert detect
