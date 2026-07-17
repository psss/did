# coding: utf-8
""" Tests for did.version """

import re

from did.version import get_version


def test_get_version_format() -> None:
    """ Version string looks like N.N.N (matches did.spec / install metadata). """
    ver = get_version()
    assert re.match(r"^\d+\.\d+\.\d+$", ver), ver
