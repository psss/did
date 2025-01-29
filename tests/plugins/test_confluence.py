# coding: utf-8
""" Tests for the Confluence plugin """

import os
import sys

import did.base
import did.cli
from did.base import ReportError
from did.plugins.confluence import ConfluenceStats

sys.path.insert(1, os.path.join(os.path.dirname(__file__), "..", ".."))


CONFIG = """
[confluence]
type = confluence
url = https://confluence.automotivelinux.org/
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Configuration tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def assert_conf_error(config, expected_error=ReportError):
    """ Test given config and check that given error type is raised """
    print(config)
    did.base.Config(config)
    dict(did.base.Config().section("confluence"))
    error = None
    try:
        ConfluenceStats("confluence")
        print("pippo")
        print(ConfluenceStats)
    except ReportError as e:
        error = e
        print(error)
    assert isinstance(error, expected_error)


def test_config_gss_auth():
    """  Test default authentication configuration """
    did.base.Config(CONFIG)
    ConfluenceStats("confluence")


def test_config_basic_auth():
    """  Test basic authentication configuration """
    did.base.Config(f"""
{CONFIG}
auth_type = basic
auth_username = tom
auth_password = motak
""")
    ConfluenceStats("confluence")


def test_config_missing_username():
    """  Test basic auth with missing username """
    assert_conf_error(f"""
{CONFIG}
auth_type = basic
""")


def test_config_missing_password():
    """  Test basic auth with missing username """
    assert_conf_error(f"""
{CONFIG}
auth_type = basic
auth_username = tom
""")


def test_config_gss_and_username():
    """  Test gss auth with username set """
    assert_conf_error(f"""
{CONFIG}
auth_type = gss
auth_username = tom
""")


def test_config_gss_and_password():
    """  Test gss auth with password set """
    assert_conf_error(f"""
{CONFIG}
auth_type = gss
auth_password = tom
""")


def test_config_gss_and_password_file():
    """  Test gss auth with password set """
    assert_conf_error(f"""
{CONFIG}
auth_type = gss
auth_password_file = ~/.did/config
""")


def test_config_invaliad_ssl_verify():
    """  Test ssl_verify with wrong bool value """
    assert_conf_error(f"""
{CONFIG}
ssl_verify = ss
""")
