
import tmt

tree = tmt.Tree('data')

def test_root():
    root = tree.tests(names=['/root'])[0]
    assert root.summary == 'Test in the root directory'
    assert root.path == '/'

def test_simple():
    simple = tree.tests(names=['/simple'])[0]
    assert simple.summary == 'Simple test in a separate directory'
    assert simple.path == '/simple'

def test_virtual():
    for virtual in tree.tests(names=['/virtual']):
        assert 'Virtual test' in virtual.summary
        assert virtual.path == '/virtual'
