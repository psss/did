# coding: utf-8
""" Tests for the Jira plugin """

from __future__ import unicode_literals, absolute_import

import sys, os
sys.path.insert(1, os.path.join(os.path.dirname(__file__), "..", ".."))

import did.cli
import did.base
from did.base import ReportError
from did.plugins.jira import JiraStats


CONFIG = """
[jira]
type = jira
prefix = JBEAP
project = JBEAP
url = https://issues.jboss.org
auth_url = https://issues.jboss.org/rest/auth/latest/session
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Configuration tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_config_gss_auth():
    """  Test default authentication configuration """
    did.base.Config(CONFIG)
    stats = JiraStats("jira")

def test_config_basic_auth():
    """  Test basic authentication configuration """
    did.base.Config(CONFIG +
                    """
                    auth_type = basic
                    auth_username = tom
                    auth_password = motak
                    """)
    stats = JiraStats("jira")

def test_config_missing_username():
    """  Test basic auth with missing username """
    assert_conf_error(CONFIG + "\n"
                    + "auth_type = basic")

def test_config_missing_password():
    """  Test basic auth with missing username """
    assert_conf_error(CONFIG + "\n"
                      + "auth_type = basic\n"
                      + "auth_username = tom\n")

def test_config_gss_and_username():
    """  Test gss auth with username set """
    assert_conf_error(CONFIG + "\n"
                    + "auth_type = gss\n"
                    + "auth_username = tom\n")

def test_config_gss_and_password():
    """  Test gss auth with password set """
    assert_conf_error(CONFIG + "\n"
                      + "auth_type = gss\n"
                      + "auth_password = tom\n")

def assert_conf_error(config, expected_error=ReportError):
    """  Test given configuration and check that given error type is raised """
    did.base.Config(config)
    error = None
    try:
        stats = JiraStats("jira")
    except ReportError as e:
        error = e
    assert type(error) == expected_error

