# coding: utf-8
""" Tests for the Jira plugin """

import logging
import os
import tempfile

import pytest
from _pytest.logging import LogCaptureFixture

import did.base
import did.cli
from did.plugins.jira import JiraStats

CONFIG = """
[general]
email = mail@example.com
[jira]
type = jira
prefix = JBEAP
project = JBEAP
url = https://issues.redhat.com/
auth_url = https://issues.redhat.com/rest/auth/latest/session
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Configuration tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_config_gss_auth():
    """  Test default authentication configuration """
    did.base.Config(CONFIG)
    JiraStats("jira")


def test_wrong_auth():
    """  Test wrong authentication type configuration """
    did.base.Config(f"""
{CONFIG}
auth_type = OAuth2
""")
    with pytest.raises(did.base.ReportError, match=r"Unsupported authentication type"):
        JiraStats("jira")


def test_config_basic_auth():
    """  Test basic authentication configuration """
    did.base.Config(f"""
{CONFIG}
auth_type = basic
auth_username = tom
auth_password = motak
""")
    stats = JiraStats("jira")
    with pytest.raises(did.base.ReportError, match="Jira authentication failed"):
        assert stats.session is not None


def test_config_basic_auth_with_password_file():
    """
    Test basic authentication configuration with a password file
    """
    with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as password_file:
        password_file.write("motak\n")
        password_file.flush()
        did.base.Config(f"""
{CONFIG}
auth_type = basic
auth_username = tom
auth_password_file = {password_file.name}
""")
        JiraStats("jira")


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


def test_ssl_verify(caplog: LogCaptureFixture):
    """Test ssl_verify """
    did.base.Config(f"""
{CONFIG}
ssl_verify = False
""")
    with caplog.at_level(logging.ERROR):
        # expected to fail authentication as we are not providing valid
        # credentials
        did.cli.main("today")
        assert "Jira authentication failed" in caplog.text


def test_jira_missing_url():
    """ Missing URL """
    assert_conf_error(CONFIG.replace("url = https://issues.redhat.com/\n", ""))


def test_jira_wrong_url(caplog: LogCaptureFixture):
    """ Missing URL """
    did.base.Config(f"""{did.base.Config.example()}
[jira]
type = jira
prefix = JBEAP
project = JBEAP
url = https://localhost
""")
    with caplog.at_level(logging.ERROR):
        did.cli.main("today")
        assert "Failed to connect to Jira" in caplog.text


def test_jira_use_scriptrunner_config_error():
    """ use_scriptrunner False and missing project """
    did.base.Config(f"""{did.base.Config.example()}
[jira]
type = jira
prefix = JBEAP
use_scriptrunner = False
url = https://issues.redhat.com/
auth_url = https://issues.redhat.com/rest/auth/latest/session
""")
    with pytest.raises(did.base.ReportError,
                       match=r"When scriptrunner is disabled.*has to be defined.*."):
        JiraStats("jira")


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
        JiraStats("jira")


def test_missing_token_expiration_when_name_is_set():
    """ `token` and `token_name` set but missing token_expiration """
    did.base.Config(f"""
{CONFIG}
auth_type = token
token = invalid_token
token_name = did
""")
    with pytest.raises(
            did.base.ReportError,
            match=r"The ``token_name`` and ``token_expiration`` must be set"
            ):
        JiraStats("jira")


def test_missing_token_name_when_expiration_is_set():
    """ `token` and `token_expiration` set but missing token_name """
    did.base.Config(f"""
{CONFIG}
auth_type = token
token = invalid_token
token_expiration = 30
""")
    with pytest.raises(
            did.base.ReportError,
            match=r"The ``token_name`` and ``token_expiration`` must be set"
            ):
        JiraStats("jira")


def test_invalid_token_expiration():
    """ `token` and `token_expiration` set but missing token_name """
    did.base.Config(f"""
{CONFIG}
auth_type = token
token = invalid_token
token_expiration = invalid_value
token_name = did
""")
    with pytest.raises(
            did.base.ReportError,
            match=r"The ``token_expiration`` must contain number"
            ):
        JiraStats("jira")


@pytest.mark.skipif("JIRA_TOKEN" not in os.environ,
                    reason="No JIRA_TOKEN environment variable found")
def test_auth_token():
    """
    Test token authentication
    """
    did.base.Config(f"""
{CONFIG}
auth_type = token
token = {os.getenv(key="JIRA_TOKEN")}
""")
    stats = JiraStats("jira")
    assert stats.token_expiration is None
    assert stats.token_name is None
    assert stats.session is not None


def assert_conf_error(config, expected_error=did.base.ReportError):
    """ Test given config and check that given error type is raised """
    did.base.Config(config)
    with pytest.raises(expected_error):
        JiraStats("jira")
