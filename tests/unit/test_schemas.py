import os
import subprocess

import pytest
from ruamel.yaml import YAML

import tmt

PATH = os.path.dirname(os.path.realpath(__file__))
SCHEMADIR = os.path.join(PATH, "../../tmt/schemas")
ROOTDIR = os.path.join(PATH, "../..")


@pytest.fixture
def schema_and_store():
    # TODO: tmt package shall provide a helper function
    # for "load schemas for test/plan/story"
    schema_file = os.path.join(SCHEMADIR, 'test.yaml')
    schema = YAML(typ="safe").load(open(schema_file, encoding="utf-8"))

    schema_store = {}

    for schema_name in ('common', 'core'):
        schema_file = os.path.join(SCHEMADIR, f'{schema_name}.yaml')
        store_schema = YAML(
            typ="safe").load(
            open(
                schema_file,
                encoding="utf-8"))
        schema_store[store_schema['$id']] = store_schema

    return schema, schema_store


@pytest.fixture(params=tmt.Tree(ROOTDIR).tests())
def test_result(request, schema_and_store):
    schema, store = schema_and_store
    return request.param.node.validate(schema, store)


def test_test_schema(test_result):
    if not test_result.result:
        for error in test_result.errors:
            print(error)

    assert test_result.result
