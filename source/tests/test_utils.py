#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import unicode_literals


def test_utils_import():
    # simple test that import works
    from status_report import utils
    assert utils


def test_email_re():
    ''' Confirm regex works as we would expect for extracting
        name, login and email from standard email strings'''
    from status_report.utils import EMAIL_REGEXP

    # good
    x = '"Chris Ward" <cward@redhat.com>'
    groups = EMAIL_REGEXP.search(x).groups()
    assert len(groups) == 2
    assert groups[0] == 'Chris Ward'
    assert groups[1] == 'cward@redhat.com'

    x = 'cward@redhat.com'
    groups = EMAIL_REGEXP.search(x).groups()
    assert len(groups) == 2
    assert groups[0] is None
    assert groups[1] == 'cward@redhat.com'

    # bad
    x = 'cward'
    groups = EMAIL_REGEXP.search(x)
    assert groups is None

    # ugly
    x = '"" <>'
    groups = EMAIL_REGEXP.search(x)
    assert groups is None


def test_ConfigError():
    ''' Confirm ConfigError exception is defined '''
    from status_report.utils import ConfigError

    try:
        raise ConfigError
    except ConfigError:
        pass
    else:
        raise RuntimeError("ConfigError exception failing!")


def test_ReportError():
    ''' Confirm ReportError exception is defined '''
    from status_report.utils import ReportError

    try:
        raise ReportError
    except ReportError:
        pass
    else:
        raise RuntimeError("ReportError exception failing!")
