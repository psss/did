import itertools
import os
import textwrap

import pytest

import tmt
import tmt.utils

PATH = os.path.dirname(os.path.realpath(__file__))
ROOTDIR = os.path.join(PATH, "../..")


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
        yield tree, node


def _iter_trees():
    yield tmt.Tree(ROOTDIR)

    # Ad hoc construction, but here me out: there are small, custom-tailored fmf trees
    # to serve various tests. These are invisible to the top-level tree. Lucky us though,
    # they are still fmf trees, therefore we can look for .fmf directories under tests/.
    #
    # TODO: disabled on purpose - when enabled, there's plenty of failed tests, including
    # those that are expected to be broken as they are used to verify `tmt lint` or similar
    # features. First we need to find a way how to get those ignored by this generator.
    # But the code below works, like a charm, and we will need to cover more trees than
    # just the root one, so leaving the code here but disabled.
    if False:
        for dirpath, dirnames, _ in os.walk(os.path.join(ROOTDIR, 'tests')):
            if '.fmf' in dirnames:
                yield tmt.Tree(dirpath)


def _iter_tests_in_tree(tree):
    yield from _iter_nodes(tree, ['test'])


def _iter_plans_in_tree(tree):
    yield from _iter_nodes(tree, ['execute'])


def _iter_stories_in_tree(tree):
    yield from _iter_nodes(tree, ['story'])


TESTS = itertools.chain.from_iterable(_iter_tests_in_tree(tree) for tree in _iter_trees())
PLANS = itertools.chain.from_iterable(_iter_plans_in_tree(tree) for tree in _iter_trees())
STORIES = itertools.chain.from_iterable(_iter_stories_in_tree(tree) for tree in _iter_trees())


def validate_node(tree, node, schema, label, name):
    errors = tmt.utils.validate_fmf_node(node, schema)

    if errors:
        print(f"""A node in tree loaded from {str(_tree_path(tree))} failed validation
""")

        for error, message in errors:
            print(f"""* {message}

Detailed validation error:

{textwrap.indent(str(error), '  ')}
""")

        assert False, f'{label} {name} fails validation'


def _tree_path(tree):
    return os.path.relpath(os.path.abspath(tree._path))


def extract_testcase_id(arg):
    if isinstance(arg, tmt.Tree):
        return _tree_path(arg)

    return arg.name


@pytest.mark.parametrize(('tree', 'test'), TESTS, ids=extract_testcase_id)
def test_tests_schema(tree, test):
    validate_node(tree, test, 'test.yaml', 'Test', test.name)


@pytest.mark.parametrize(('tree', 'story'), STORIES, ids=extract_testcase_id)
def test_stories_schema(tree, story):
    validate_node(tree, story, 'story.yaml', 'Story', story.name)


@pytest.mark.parametrize(('tree', 'plan'), PLANS, ids=extract_testcase_id)
def test_plans_schema(tree, plan):
    validate_node(tree, plan, 'plan.yaml', 'Plan', plan.name)
