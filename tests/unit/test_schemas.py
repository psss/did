import os

import pytest

import tmt
import tmt.utils

PATH = os.path.dirname(os.path.realpath(__file__))
SCHEMADIR = os.path.join(PATH, "../../tmt/schemas")
ROOTDIR = os.path.join(PATH, "../..")


@pytest.fixture
def tests_schema():
    return tmt.utils.load_schema('test.yaml')


@pytest.fixture
def stories_schema():
    return tmt.utils.load_schema('story.yaml')


@pytest.fixture
def plans_schema():
    return tmt.utils.load_schema('plan.yaml')


@pytest.fixture
def schema_store():
    return tmt.utils.load_schema_store()


@pytest.fixture(params=tmt.Tree(ROOTDIR).tests())
def test_validation_result(request, schema_store, tests_schema):
    node = request.param.node
    return node.name, node.validate(tests_schema, schema_store)


@pytest.fixture(params=tmt.Tree(ROOTDIR).stories())
def story_validation_result(request, schema_store, stories_schema):
    node = request.param.node
    return node.name, node.validate(stories_schema, schema_store)


@pytest.fixture(params=tmt.Tree(ROOTDIR).plans())
def plan_validation_result(request, schema_store, plans_schema):
    node = request.param.node
    return node.name, node.validate(plans_schema, schema_store)


def test_tests_schema(test_validation_result):
    name, result = test_validation_result
    if not result.result:
        for error in result.errors:
            print(error)

    assert result.result, f'Test {name} fails validation'


def test_stories_schema(story_validation_result):
    name, result = story_validation_result
    if not result.result:
        for error in result.errors:
            print(error)

    assert result.result, f'Story {name} fails validation'


def test_plans_schema(plan_validation_result):
    name, result = plan_validation_result
    if not result.result:
        for error in result.errors:
            print(error)

    assert result.result, f'Plan {name} fails validation'
