# coding: utf-8

import configparser
import datetime
import sys
import unittest
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from unittest.mock import patch
from uuid import uuid4

import pytest

import did.base

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Config
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_config_example():
    assert did.base.Config.example() == \
        "[general]\nemail = Name Surname <email@example.org>\n"


def test_config_file_error_raised_if_file_is_missing():
    with pytest.raises(
            did.base.ConfigFileError,
            match=r"Unable to read the config file"
            ):
        did.base.Config(path="/tmp/does_not_exist")


def test_config_correctly_parses_email():
    config = did.base.Config("[general]\nemail = email@example.com\n")
    assert config.email == "email@example.com"


def test_config_raises_error_with_missing_sections():
    with pytest.raises(configparser.MissingSectionHeaderError):
        did.base.Config("email = email@example.com\n")


def test_config_properties():
    config = did.base.Config(did.base.Config.example())
    assert config.plugins is None
    config = did.base.Config("""
[general]
email = email@example.com
plugins = custom
[test1]
type = git
[test2]
type = github
""")
    assert config.separator == did.base.DEFAULT_SEPARATOR
    assert config.separator_width == did.base.MAX_WIDTH
    assert config.plugins == "custom"
    assert config.sections() == ["general", "test1", "test2"]
    assert config.sections(kind="git") == ["test1"]
    assert str(config.item("test1", "type")) == "git"
    with pytest.raises(did.base.ConfigError):
        config.item("test1", "bad_typo")
    with patch.object(sys, 'argv', ["did", "--config", "/tmp/does_not_exist"]):
        assert config.path() == "/tmp/does_not_exist"


def test_config_raise_error_if_email_is_missing():
    config = did.base.Config("[general]\n")
    with pytest.raises(did.base.ConfigError):
        _ = config.email
    config = did.base.Config("[missing]")
    with pytest.raises(did.base.ConfigError):
        _ = config.email


def test_config_sets_width_properly():
    config = did.base.Config("[general]\n")
    assert config.width == did.base.MAX_WIDTH
    config = did.base.Config("[general]\nwidth = 123\n")
    assert config.width == 123


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Date
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_date_works_properly():
    assert str(did.base.Date('2018-12-01')) == '2018-12-01'
    with pytest.raises(did.base.OptionError, match=r"Invalid date format"):
        did.base.Date('2018-12-broken')


@pytest.fixture
def _mock_today():
    original_today = datetime.date.today()
    did.base.TODAY = datetime.date(2015, 10, 3)
    yield
    did.base.TODAY = original_today


@pytest.fixture
def _mock_today_quarter():
    original_today = datetime.date.today()
    did.base.TODAY = datetime.date(2015, 9, 3)
    yield
    did.base.TODAY = original_today


@pytest.mark.usefixtures("_mock_today_quarter")
def test_middle_q():
    """ Quarter periods with today in middle of a quarter """
    # pylint:disable=unused-argument,redefined-outer-name
    quarter_cases = [
        ("quarter", "2015-07-01", "2015-10-01", "this quarter"),
        ("this quarter", "2015-07-01", "2015-10-01", "this quarter"),
        ]
    # Run all test cases
    for argument, expected_since, expected_until, expected_period in quarter_cases:
        since, until, period = did.base.Date.period(argument)
        assert str(since) == expected_since
        assert str(until) == expected_until
        assert period == expected_period


@pytest.mark.usefixtures("_mock_today")
def test_ofsetted_quarters():
    """ quarters not starting on first month of the year """
    # pylint:disable=unused-argument,redefined-outer-name
    config = did.base.Config("[general]\nquarter = 2")
    assert config.quarter == 2
    config = did.base.Config("[general]\nquarter = broken")
    with pytest.raises(did.base.ConfigError, match=r"Invalid quarter start"):
        _ = config.quarter


@pytest.mark.usefixtures("_mock_today")
def test_date_period():  # pylint:disable=redefined-outer-name
    did.base.Config(did.base.Config.example())
    test_cases = [
        # Single day periods
        ("today", "2015-10-03", "2015-10-04", "today"),
        ("yesterday", "2015-10-02", "2015-10-03", "yesterday"),
        ("monday", "2015-09-28", "2015-09-29", "the last monday"),
        ("saturday", "2015-09-26", "2015-09-27", "the last saturday"),
        ("last monday", "2015-09-28", "2015-09-29", "the last monday"),
        ("last tuesday", "2015-09-29", "2015-09-30", "the last tuesday"),
        ("last wednesday", "2015-09-30", "2015-10-01", "the last wednesday"),
        ("last thursday", "2015-10-01", "2015-10-02", "the last thursday"),
        ("last friday", "2015-10-02", "2015-10-03", "the last friday"),
        ("last month", "2015-09-01", "2015-10-01", "September"),
        ("last quarter", "2015-07-01", "2015-10-01", "the last quarter"),
        ("last year", "2014-01-01", "2015-01-01", "the last year"),
        ]

    # Week periods
    week_cases = [
        ("", "2015-09-28", "2015-10-05", "the week 40"),
        ("broken", "2015-09-28", "2015-10-05", "the week 40"),
        ("week", "2015-09-28", "2015-10-05", "the week 40"),
        ("this week", "2015-09-28", "2015-10-05", "the week 40"),
        ("last", "2015-09-21", "2015-09-28", "the week 39"),
        ("last week", "2015-09-21", "2015-09-28", "the week 39"),
        ]
    test_cases.extend(week_cases)

    # Month periods
    month_cases = [
        ("month", "2015-10-01", "2015-11-01", "October"),
        ("this month", "2015-10-01", "2015-11-01", "October"),
        ]
    test_cases.extend(month_cases)

    # Quarter periods
    quarter_cases = [
        ("quarter", "2015-10-01", "2016-01-01", "this quarter"),
        ("this quarter", "2015-10-01", "2016-01-01", "this quarter"),
        ]
    test_cases.extend(quarter_cases)

    # Year periods
    year_cases = [
        ("year", "2015-01-01", "2016-01-01", "this year"),
        ("this year", "2015-01-01", "2016-01-01", "this year"),
        ]
    test_cases.extend(year_cases)

    # Run all test cases
    for argument, expected_since, expected_until, expected_period in test_cases:
        since, until, period = did.base.Date.period(argument)
        assert str(since) == expected_since
        assert str(until) == expected_until
        assert period == expected_period


def test_date_addition_subtraction():
    assert str(did.base.Date('2018-11-29') + 1) == '2018-11-30'
    assert str(did.base.Date('2018-11-29') + 2) == '2018-12-01'
    assert str(did.base.Date('2018-12-02') - 1) == '2018-12-01'
    assert str(did.base.Date('2018-12-02') - 2) == '2018-11-30'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  User
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_user_class():
    assert did.base.User

    # No email provided
    with pytest.raises(did.base.ConfigError, match="Email required"):
        did.base.User("")

    # Invalid email address
    with pytest.raises(did.base.ConfigError, match="Invalid email address"):
        did.base.User("bad-email")

    # Short email format
    user = did.base.User("some@email.org")
    assert user.email == "some@email.org"
    assert user.login == "some"
    assert user.name is None
    assert str(user) == "some@email.org"

    # Full email format
    user = did.base.User("Some Body <some@email.org>")
    assert user.email == "some@email.org"
    assert user.login == "some"
    assert user.name == "Some Body"
    assert str(user) == "Some Body <some@email.org>"

    # Invalid alias definition
    with pytest.raises(did.base.ConfigError, match="Invalid alias definition"):
        did.base.User("some@email.org; bad-alias", stats="bz")

    # Custom email alias
    user = did.base.User("some@email.org; bz: bugzilla@email.org", stats="bz")
    assert user.email == "bugzilla@email.org"
    assert user.login == "bugzilla"
    # section doesn't exist
    assert user.alias("bz: bugzilla@email.org", stats="broken") is None

    # Custom login alias
    user = did.base.User("some@email.org; bz: bzlogin", stats="bz")
    assert user.login == "bzlogin"

    # Custom email alias in config section
    did.base.Config(config="[bz]\ntype = bugzilla\nemail = bugzilla@email.org")
    user = did.base.User("some@email.org", stats="bz")
    assert user.email == "bugzilla@email.org"
    assert user.login == "bugzilla"

    # Custom login alias in config section
    did.base.Config(config="[bz]\ntype = bugzilla\nlogin = bzlogin")
    user = did.base.User("some@email.org", stats="bz")
    assert user.login == "bzlogin"

    # User cloning
    user = did.base.User("some@email.org; bz: bzlogin")
    clone = user.clone("bz")
    assert clone.login == "bzlogin"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Exceptions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_configerror_exception():
    ''' Confirm ConfigError exception is defined '''
    try:
        raise did.base.ConfigError
    except did.base.ConfigError:
        pass


def test_reporterror_exception():
    ''' Confirm ReportError exception is defined '''
    try:
        raise did.base.ReportError
    except did.base.ReportError:
        pass


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Token handling
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TestGetToken(unittest.TestCase):
    """ Tests for the `get_token` function """

    @contextmanager
    def get_token_as_file(self, token):
        """
        Returns a temporary filename with the given token written to it.
        Use this as a context manager:

            with self.get_token_as_file(token="foobar") as filename:
                config = {"token_file": filename.name}
        """
        file_handle = NamedTemporaryFile(mode="w+", encoding="utf-8")
        file_handle.writelines(token)
        file_handle.flush()
        try:
            yield file_handle.name
        finally:
            file_handle.close()

    def test_get_token_none(self):
        """ Test getting a token when none is specified """
        assert did.base.get_token({}) is None

    def test_get_token_plain(self):
        """ Test getting a token when specified in plain config file """
        token = str(uuid4())
        config = {"token": token}
        assert did.base.get_token(config) == token

    def test_get_token_plain_empty(self):
        """ Test getting a token when it is empty or just whitespace """
        config = {"token": "   "}
        assert did.base.get_token(config) is None

    def test_get_token_plain_different_name(self):
        """ Test getting a plain token under a different name """
        token = str(uuid4())
        config = {"mytoken": token}
        assert did.base.get_token(config) is None
        assert did.base.get_token(config, token_key="mytoken") == token

    def test_get_token_file(self):
        """ Test getting a token from a file """
        token_in_file = str(uuid4())
        with self.get_token_as_file(token_in_file) as filename:
            config = {"token_file": filename}
            assert did.base.get_token(config) == token_in_file

    def test_get_token_file_empty(self):
        """ Test getting a token from a file with just whitespace. """
        token_in_file = "   "
        with self.get_token_as_file(token_in_file) as filename:
            config = {"token_file": filename}
            assert did.base.get_token(config) is None

    def test_get_token_precedence(self):
        """ Test plain token precedence over file one """
        token_plain = str(uuid4())
        token_in_file = str(uuid4())
        with self.get_token_as_file(token_in_file) as filename:
            config = {"token_file": filename, "token": token_plain}
            assert did.base.get_token(config) == token_plain

    def test_get_token_file_different_name(self):
        """ Test getting a token from a file under different name """
        token_in_file = str(uuid4())
        with self.get_token_as_file(token_in_file) as filename:
            config = {"mytoken_file": filename}
            assert did.base.get_token(
                config, token_file_key="mytoken_file") == token_in_file
