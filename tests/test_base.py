# coding: utf-8

from __future__ import unicode_literals, absolute_import

from datetime import date, datetime
import did.base
import pytest
import pytz

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

def test_TODAY():
    from did.base import TODAY

    d = TODAY.date()
    _d = datetime.utcnow().replace(tzinfo=pytz.utc).date()
    assert d == _d


def test_import_Date():
    from did.base import Date
    assert Date


def test_Date_type_handling():
    from did.base import Date

    # clearly not dates
    BAD_DATES = [int(1), 'BAD DATE']
    for bad in BAD_DATES:
        with pytest.raises(did.base.OptionError):
            Date(bad)

    # Date, no timezone or time even
    D_today = date(2015, 1, 1)
    d_today = '2015-01-01'
    assert unicode(Date(d_today)) == d_today
    assert unicode(Date(D_today)) == d_today
    # should always have utc timezone attached
    assert Date(d_today).date.tzinfo == pytz.utc

    # UTC
    DT_today_utc = datetime(2015, 1, 1, 0, 0, 0, tzinfo=UTC)
    dt_today_utc = '2015-01-01 00:00:00.000 +0000'
    assert unicode(Date(dt_today_utc)) == d_today
    # should always have utc timezone attached
    # so this is the last time we test for it since it's been found 2x already
    assert Date(dt_today_utc).date.tzinfo == pytz.utc

    # UTC using 'T' instead of ' ' (space) between date and time
    dt_today_utc = '2015-01-01T00:00:00.000 +0000'
    #                         ^
    assert unicode(Date(dt_today_utc)) == d_today
    DT_today_utc = datetime(2015, 1, 1, 0, 0, 0, tzinfo=UTC)
    # Try with datetime
    assert unicode(Date(DT_today_utc)) == d_today

    # CET
    DT_today_cet = datetime(2015, 1, 1, 0, 0, 0, tzinfo=CET)
    dt_today_cet = '2015-01-01 00:00:00.000 +0200'
    d_today_UTC_from_CET = '2014-12-31'
    assert unicode(Date(dt_today_cet)) == d_today_UTC_from_CET
    assert unicode(Date(DT_today_cet)) == d_today_UTC_from_CET

    # UNSPECIFIED timezone (assumed UTC)
    DT_today_x = datetime(2015, 1, 1, 0, 0, 0)
    dt_today_x = '2015-01-01 00:00:00'
    assert unicode(Date(dt_today_x)) == d_today
    assert unicode(Date(DT_today_x)) == d_today

    # CET specific time, 12:00:00
    dt_today_noon_cet = '2015-01-01 12:00:00 +0200'
    iso = '%Y-%m-%d %H:%M:%S %z'

    _DT = unicode(Date(dt_today_noon_cet, fmt=iso))
    dt_today_noon_cet_as_utc = '2015-01-01 10:00:00 +0000'
    assert _DT == dt_today_noon_cet_as_utc


def test_Date_period():
    from did.base import Date
    # WARN: THIS EFFECTS OTHER TESTS! THIS IS NOT AN
    # ISSOLATED UPDATE; IT BROKE TESTS; RESETTING BACK
    # TO ORIGINAL STATE AT THE END NOW
    try:
        _TODAY = did.base.TODAY
        did.base.TODAY = date(2015, 10, 3)
        # This week
        for argument in ["", "week", "this week"]:
            since, until, period = Date.period(argument)
            assert unicode(since) == "2015-09-28"
            assert unicode(until) == "2015-10-05"
            assert period == "this week"
        # Last week
        for argument in ["last", "last week"]:
            since, until, period = Date.period(argument)
            assert unicode(since) == "2015-09-21"
            assert unicode(until) == "2015-09-28"
            assert period == "the last week"
        # This month
        for argument in ["month", "this month"]:
            since, until, period = Date.period(argument)
            assert unicode(since) == "2015-10-01"
            assert unicode(until) == "2015-11-01"
            assert period == "this month"
        # Last month
        for argument in ["last month"]:
            since, until, period = Date.period(argument)
            assert unicode(since) == "2015-09-01"
            assert unicode(until) == "2015-10-01"
            assert period == "the last month"
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
    finally:
        # RESET the did.base module state back to original...
        did.base.TODAY = _TODAY


def test_Date_format():
    from did.base import Date

    d = '2015-01-01'
    dt = '2015-01-01 00:00:00'
    dtz = '2015-01-01 00:00:00 +0000'
    dtz_cet = '2015-01-01 00:00:00 +0200'
    # since we're 2 hours ahead, in UTC we're 2 behind
    dtz_cet_utc = '2014-12-31 22:00:00 +0000'
    d_cet_utc = '2014-12-31'

    # Default format will return the date in YYYY-MM-DD form
    # after date conversion from defined timezone to UTC, if
    # timezone is set on the incoming date value.
    assert str(Date(d)) == d
    assert str(Date(dt)) == str(d)
    assert str(Date(dtz)) == str(d)
    assert str(Date(dtz_cet)) == str(d_cet_utc)

    # different formats should all work as strftime() expects
    fmt = '%Y'
    assert str(Date(d, fmt=fmt)) == '2015'
    fmt = '%Y-%m-%d'
    assert str(Date(d, fmt=fmt)) == d
    fmt = '%Y-%m-%d %H:%M:%S'
    assert str(Date(dt, fmt=fmt)) == dt
    fmt = '%Y-%m-%d %H:%M:%S %z'
    assert str(Date(dt, fmt=fmt)) == dtz
    assert str(Date(d, fmt=fmt)) == dtz

    # unicode works as expected
    assert unicode(Date('2015-01-01')) == unicode(d)

    # specify timezone
    iso = '%Y-%m-%d %H:%M:%S %z'
    assert unicode(Date(dtz_cet, fmt=iso)) == dtz_cet_utc


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
