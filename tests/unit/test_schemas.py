import os

import pytest

import tmt
import tmt.utils

PATH = os.path.dirname(os.path.realpath(__file__))
ROOTDIR = os.path.join(PATH, "../..")

TREE = tmt.Tree(ROOTDIR)


# This is what `Tree.{tests,plans,stories}`` do internally, but after getting
# all nodes, these methods would construct tmt objects representing found
# nodes. That is *not* what we want, because the act of instantiating a `Plan``
# object, for example, would affect content of the corresponding node, e.g.
# `Plan` class would add some missing keys, using predefined default values.
#
# We want raw nodes here, therefore we need to get our hands on them before
# `Tree` modifies them - use the underlying fmf tree's `prune()` method, and
# use the right keys to filter out nodes we're interested in (the same `Tree`
# uses).
def _iter_nodes(tree, keys):
    for node in tree.tree.prune(keys=keys):
        yield node


def iter_tests(tree):
    yield from _iter_nodes(tree, ['test'])


def iter_plans(tree):
    yield from _iter_nodes(tree, ['execute'])


def iter_stories(tree):
    yield from _iter_nodes(tree, ['story'])


# pytest.mark.parametrize expects us to deliver an iterable for each test invocation,
# and since there's only a single argument for our test cases, the node to validate,
# we need to construct the iterable with this single item.
def as_parameters(nodes):
    for node in nodes:
        yield (node,)


TESTS = list(as_parameters(iter_tests(TREE)))
PLANS = list(as_parameters(iter_plans(TREE)))
STORIES = list(as_parameters(iter_stories(TREE)))


def validate_node(node, schema, label, name):
    errors = tmt.utils.validate_fmf_node(node, schema)

    if errors:
        for error, message in errors:
            print(f'* {message}')
            print(f'    {error}')
            print()

        assert False, f'{label} {name} fails validation'


@pytest.mark.parametrize(('test',), TESTS, ids=lambda node: node.name)
def test_tests_schema(test):
    validate_node(test, 'test.yaml', 'Test', test.name)


@pytest.mark.parametrize(('story',), STORIES, ids=lambda node: node.name)
def test_stories_schema(story):
    validate_node(story, 'story.yaml', 'Story', story.name)


@pytest.mark.parametrize(('plan',), PLANS, ids=lambda node: node.name)
def test_plans_schema(plan):
    validate_node(plan, 'plan.yaml', 'Plan', plan.name)
