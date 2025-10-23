# coding: utf-8
""" Tests for the Jira plugin """

import logging
import os
import re
import tempfile

import pytest
from _pytest.logging import LogCaptureFixture

import did.base
import did.cli
from did.plugins.jira import JiraStats, JiraWorklog

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


def has_worklog_stat() -> bool:
    """ Returns true if a fresh initiated JiraStats
    object would have a JiraWorklog object """
    stats = JiraStats("jira")
    for stat in stats.stats:
        if isinstance(stat, JiraWorklog):
            return True
    return False


@pytest.mark.parametrize(  # type: ignore[misc]
    ("config_str", "expected_worklog_enable"),
    [
        (f"""
{CONFIG}
""", False),
        (f"""
{CONFIG}
worklog_enable = on
""", True),
        (f"""
{CONFIG}
worklog_enable = off
""", False),
        ],
    )
def test_worklog_enabled(
        config_str: str,
        expected_worklog_enable: bool,
        ) -> None:
    """ Tests default and explicit behaviour for worklog_enable """
    did.base.Config(config_str)
    assert has_worklog_stat() == expected_worklog_enable


def get_named_stat(options: str):
    """
    Retrieve the statistics by option name.
    """
    for stat in did.cli.main(f"{options}")[0][0].stats[0].stats:
        if stat.option in options:
            assert stat.stats is not None
            return stat.stats
    pytest.fail(reason=f"No stat found with options {options}")
    return None


def test_worklog_against_real_jira_instance() -> None:
    """ Check that worklogs are printed for matching issues """
    # I've searched a public Jira instance and found this issue
    # that has worklog entries:
    # https://issues.apache.org/jira/browse/HIVE-21563
    # The user "githubbot" has more entries in other issues
    # that we've limited to certain day.
    did.base.Config("""
[general]
email = mail@example.com
width = 500
[jira]
type = jira
prefix = HIVE
project = HIVE
login = githubbot
url = https://issues.apache.org/jira/
worklog_enable = on
""")
    # auth_url = https://issues.apache.org/jira/rest/auth/latest/session
    options = "--jira-worklog --since 2021-05-07 --until 2021-05-07 --verbose"
    stats = get_named_stat(options)
    expectations = [
        {
            "id": "HIVE-25095",
            "worklog_snippets": [
                "* Worklog: Friday, May 07, 2021 (10m)",
                "ujc714 opened a new pull request #2255:",
                ]
            },
        {
            "id": "HIVE-25089",
            "worklog_snippets": [
                "* Worklog: Friday, May 07, 2021 (10m)",
                "kasakrisz merged pull request #2241:",
                ]},
        {
            "id": "HIVE-25071",
            "worklog_snippets": [
                "* Worklog: Friday, May 07, 2021 (10m)",
                "kasakrisz commented on a change in pull request #2231:",
                ]},
        {
            "id": "HIVE-25046",
            "worklog_snippets": [
                "* Worklog: Friday, May 07, 2021 (10m)",
                "zabetak commented on a change in pull request #2205:"
                ]
            }, {
            "id": "HIVE-23756",
            "worklog_snippets": [
                "* Worklog: Friday, May 07, 2021 (10m)",
                "scarlin-cloudera closed pull request #2253:",
                "* Worklog: Friday, May 07, 2021 (10m)",
                "scarlin-cloudera opened a new pull request #2254:"
                ]
            }, {
            "id": "HIVE-21563",
            "worklog_snippets": [
                "* Worklog: Friday, May 07, 2021 (10m)",
                "sunchao merged pull request #2251:",
                ]},
        ]
    assert len(expectations) == len(stats)
    for i, exp in enumerate(expectations):
        stat_str = str(stats[i])

        # Check that the issue with the given ID was found
        id_pattern = f"{exp["id"]} \\S+"
        # if "--verbose" in options:
        #     pattern = f"https://reviews\\.llvm\\.org/{exp_id} \\S+"
        regex = re.compile(id_pattern)
        assert regex
        assert regex.match(stat_str)

        # Check that for each issue we find the expected
        # worklog snippets one after the next
        start = 0
        for worklog_snippet in exp["worklog_snippets"]:
            new_start = stat_str.find(worklog_snippet, start)
            assert new_start > 0, (f"worklog_snippet '{worklog_snippet}' "
                                   "not found in stat string from position "
                                   "{start}: {stat_str}")
            start = new_start
