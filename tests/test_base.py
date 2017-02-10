# coding: utf-8

from __future__ import unicode_literals, absolute_import

import pytest
import datetime
import did.base
from did.base import Config, ConfigError

def test_base_import():
    # simple test that import works
    from did import base
    assert base


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Config
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_Config():
    from did.base import Config
    assert Config

def test_Config_email():
    config = Config("[general]\nemail = email@example.com\n")
    assert config.email == "email@example.com"

def test_Config_email_missing():
    config = Config("[general]\n")
    with pytest.raises(did.base.ConfigError):
        config.email == "email@example.com"
    config = Config("[missing]")
    with pytest.raises(did.base.ConfigError):
        config.email == "email@example.com"

def test_Config_width():
    config = Config("[general]\n")
    assert config.width == did.base.MAX_WIDTH
    config = Config("[general]\nwidth = 123\n")
    assert config.width == 123


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Date
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_Date():
    from did.base import Date
    assert Date


def test_Date_period():
    from did.base import Date
    today = did.base.TODAY
    did.base.TODAY = datetime.date(2015, 10, 3)
    # yesterday
    for argument in ["yesterday"]:
        since, until, period = Date.period(argument)
        assert unicode(since) == "2015-10-02"
        assert unicode(until) == "2015-10-03"
        assert period == "yesterday"
    # This week
    for argument in ["", "week", "this week"]:
        since, until, period = Date.period(argument)
        assert unicode(since) == "2015-09-28"
        assert unicode(until) == "2015-10-05"
        assert period == "the week 40"
    # Last week
    for argument in ["last", "last week"]:
        since, until, period = Date.period(argument)
        assert unicode(since) == "2015-09-21"
        assert unicode(until) == "2015-09-28"
        assert period == "the week 39"
    # This month
    for argument in ["month", "this month"]:
        since, until, period = Date.period(argument)
        assert unicode(since) == "2015-10-01"
        assert unicode(until) == "2015-11-01"
        assert period == "October"
    # Last month
    for argument in ["last month"]:
        since, until, period = Date.period(argument)
        assert unicode(since) == "2015-09-01"
        assert unicode(until) == "2015-10-01"
        assert period == "September"
    # This quarter
    for argument in ["quarter", "this quarter"]:
        since, until, period = Date.period(argument)
        assert unicode(since) == "2015-09-01"
        assert unicode(until) == "2015-12-01"
        assert period == "this quarter"
    # Last quarter
    for argument in ["last quarter"]:
        since, until, period = Date.period(argument)
        assert unicode(since) == "2015-06-01"
        assert unicode(until) == "2015-09-01"
        assert period == "the last quarter"
    # This year
    for argument in ["year", "this year"]:
        since, until, period = Date.period(argument)
        assert unicode(since) == "2015-03-01"
        assert unicode(until) == "2016-03-01"
        assert period == "this fiscal year"
    # Last year
    for argument in ["last year"]:
        since, until, period = Date.period(argument)
        assert unicode(since) == "2014-03-01"
        assert unicode(until) == "2015-03-01"
        assert period == "the last fiscal year"
    did.base.TODAY = today


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  User
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_User():
    from did.base import User
    assert User

    # No email provided
    try:
        user = User("")
    except ConfigError:
        pass
    else:
        raise RuntimeError("No exception for missing email")

    # Invalid email address
    try:
        user = User("bad-email")
    except ConfigError:
        pass
    else:
        raise RuntimeError("No exception for invalid email")

    # Short email format
    user = User("some@email.org")
    assert user.email == "some@email.org"
    assert user.login == "some"
    assert user.name == None
    assert unicode(user) == "some@email.org"

    # Full email format
    user = User("Some Body <some@email.org>")
    assert user.email == "some@email.org"
    assert user.login == "some"
    assert user.name == "Some Body"
    assert unicode(user) == "Some Body <some@email.org>"

    # Invalid alias definition
    try:
        user = User("some@email.org; bad-alias", stats="bz")
    except ConfigError:
        pass
    else:
        raise RuntimeError("No exception for invalid alias definition")

    # Custom email alias
    user = User("some@email.org; bz: bugzilla@email.org", stats="bz")
    assert user.email == "bugzilla@email.org"
    assert user.login == "bugzilla"

    # Custom login alias
    user = User("some@email.org; bz: bzlogin", stats="bz")
    assert user.login == "bzlogin"

    # Custom email alias in config section
    Config(config="[bz]\ntype = bugzilla\nemail = bugzilla@email.org")
    user = User("some@email.org", stats="bz")
    assert user.email == "bugzilla@email.org"
    assert user.login == "bugzilla"

    # Custom login alias in config section
    Config(config="[bz]\ntype = bugzilla\nlogin = bzlogin")
    user = User("some@email.org", stats="bz")
    assert user.login == "bzlogin"

    # User cloning
    user = User("some@email.org; bz: bzlogin")
    clone = user.clone("bz")
    assert clone.login == "bzlogin"



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Exceptions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_ConfigError():
    ''' Confirm ConfigError exception is defined '''
    from did.base import ConfigError

    try:
        raise ConfigError
    except ConfigError:
        pass
    else:
        raise RuntimeError("ConfigError exception failing!")


def test_ReportError():
    ''' Confirm ReportError exception is defined '''
    from did.base import ReportError

    try:
        raise ReportError
    except ReportError:
        pass
    else:
        raise RuntimeError("ReportError exception failing!")
