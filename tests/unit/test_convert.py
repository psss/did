# coding: utf-8
from textwrap import dedent

from tmt.convert import extract_relevancy
from tmt.utils import StructuredField


def test_extract_relevancy_field_has_priority():
    notes = dedent("""
    relevancy:
    distro == fedora: False

    [structured-field-start]
    This is StructuredField version 1. Please, edit with care.

    [relevancy]
    distro == rhel: False

    [structured-field-end]
  """)

    field = StructuredField(notes)
    relevancy = extract_relevancy(notes, field)
    assert relevancy == "distro == rhel: False\n"
