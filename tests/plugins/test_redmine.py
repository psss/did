# coding: utf-8
""" Tests for the Redmine plugin """

# import did.base
# import did.cli

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

INTERVAL = "--since 2020-01-01 --until 2020-02-01"

CONFIG = """
[general]
email = "Ignored" <ignored@redhat.com>

[redmine]
type = redmine
url = https://projects.theforeman.org
login = 4731
"""

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# def test_redmine_activity():
#    """ Redmine activity """
#    did.base.Config(CONFIG)
#    option = "--redmine-activity "
#    stats = did.cli.main(
#       option + INTERVAL)[0][0].stats[0].stats[0].stats
#    assert any(
#        ["Candlepin fails to talk" in str(stat) for stat in stats])
