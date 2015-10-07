# -*- coding: utf-8 -*-
# @Author: Chris Ward

""" Tests for the Idonethis plugin """

from __future__ import unicode_literals, absolute_import

import pytest
import did.cli
import did.base

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

_C = CONFIG_NO_TOKEN = """
[general]
email = "Chris Ward" <cward@redhat.com>

[idonethis]
type = idonethis
"""

CONFIG_BAD_TOKEN = _C + '\ntoken = NOT_A_VALID_TOKEN'
# test token created by "Chris Ward" <kejbaly2@gmail.com>
CONFIG_OK = _C + '\ntoken = 480710a894e756a27ef9d812f2309b8b2cd9dd4e'

INTERVAL = "--since 2015-10-06 --until 2015-10-07"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Sanity Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_import():
    """  Test basic module import """
    from did.plugins.idonethis import IdonethisStats
    assert IdonethisStats


def test_missing_token():
    """
    Missing apitoken results in Exception
    """
    import did
    did.base.Config(CONFIG_NO_TOKEN)
    with pytest.raises(did.base.ConfigError):
        did.cli.main(INTERVAL)


def test_invalid_token():
    """ Invalid bitly token """
    import did
    did.base.Config(CONFIG_BAD_TOKEN)
    with pytest.raises(did.base.ReportError):
        did.cli.main(INTERVAL)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Acceptance Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def test_all_dones():
    """ test that dones stats are queried as expected """
    did.base.Config(CONFIG_OK)
    result = did.cli.main(INTERVAL)
    stats = result[0][0].stats[0].stats[0].stats
    assert len(stats) == 5
    _stats = [u'[2015-10-07] <kejbaly2_did_test> [ ] did goal test 1',
              u'[2015-10-06] <kejbaly2_did_test> [x] did goal done test 2',
              u'[2015-10-06] <kejbaly2_did_test> did done test 1',
              u'[2015-10-06] <kejbaly2_did_test> did done test 2',
              u'[2015-10-06] <kejbaly2_did_test> did done test 3']
    assert sorted(_stats) == sorted(stats)
