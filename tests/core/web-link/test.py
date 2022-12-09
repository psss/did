import re

import tmt

tree = tmt.Tree(path='data')
prefix = r'https://github.com/.*/tmt/tree/.*/tests/core/web-link/data/'


def test_stories():
    url = tree.stories(names=['/story'])[0].web_link()
    assert re.match(prefix + 'story.fmf', url)


def test_plans():
    url = tree.plans(names=['/plan'])[0].web_link()
    assert re.match(prefix + 'plan.fmf', url)


def test_tests():
    url = tree.tests(names=['/test'])[0].web_link()
    assert re.match(prefix + 'test.fmf', url)
