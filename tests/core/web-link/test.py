import tmt

tree = tmt.Tree(path='data')


def test_stories():
    url = tree.stories(names=['/story'])[0].web_link()
    assert url.startswith('https://github.com/teemtee/tmt/tree/')
    assert url.endswith('/tests/core/web-link/data/story.fmf')


def test_plans():
    url = tree.plans(names=['/plan'])[0].web_link()
    assert url.startswith('https://github.com/teemtee/tmt/tree/')
    assert url.endswith('/tests/core/web-link/data/plan.fmf')


def test_tests():
    url = tree.tests(names=['/test'])[0].web_link()
    assert url.startswith('https://github.com/teemtee/tmt/tree/')
    assert url.endswith('/tests/core/web-link/data/test.fmf')
