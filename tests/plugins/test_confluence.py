# coding: utf-8
""" Tests for the Confluence plugin """

import pytest

import did.base
import did.cli
from did.plugins.confluence import ConfluenceStats

CONFIG = """
[general]
email = mail@example.com

[confluence]
type = confluence
url = https://confluence.automotivelinux.org/
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Configuration tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def assert_conf_error(config, expected_error=did.base.ReportError):
    """ Test given config and check that given error type is raised """
    did.base.Config(config)
    with pytest.raises(expected_error):
        ConfluenceStats("confluence")


def test_config_auth_url():
    """  Test authentication url in configuration """
    did.base.Config(f"""
{CONFIG}
auth_url = https://confluence.automotivelinux.org/step-auth-gss
""")
    ConfluenceStats("confluence")


def test_config_gss_auth():
    """  Test default authentication configuration """
    did.base.Config(CONFIG)
    ConfluenceStats("confluence")


def test_wrong_auth():
    """  Test wrong authentication type configuration """
    did.base.Config(f"""
{CONFIG}
auth_type = OAuth2
""")
    with pytest.raises(did.base.ReportError, match=r"Unsupported authentication type"):
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


def test_confluence_config_invaliad_ssl_verify():
    """  Test ssl_verify with wrong bool value """
    assert_conf_error(f"""
{CONFIG}
ssl_verify = ss
""")


def test_confluence_ssl_verify():
    """Test ssl_verify """
    did.base.Config(f"""
{CONFIG}
ssl_verify = False
""")
    with pytest.raises(did.base.ReportError, match=r"Confluence authentication failed"):
        # expected to fail authentication as we are not providing valid
        # credentials
        did.cli.main("today")


def test_confluence_missing_url():
    """ Missing URL """
    assert_conf_error(
        CONFIG.replace(
            "url = https://confluence.automotivelinux.org/\n",
            ""))


def test_confluence_wrong_url():
    """ Missing URL """
    did.base.Config(f"""{did.base.Config.example()}
[confluence]
type = confluence
url = https://localhost
""")
    with pytest.raises(did.base.ReportError, match=r"Failed to connect to Confluence"):
        did.cli.main("today")


def test_missing_token():
    """ `token` and `token_file` missing with token auth """
    did.base.Config(f"""
{CONFIG}
auth_type = token
token_expiration = 30
""")
    with pytest.raises(
            did.base.ReportError, match=r"The `token` or `token_file` key must be set"
            ):
        ConfluenceStats("confluence")
