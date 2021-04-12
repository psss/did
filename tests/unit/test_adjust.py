import pytest

import tmt
from tmt.utils import ConvertError
from tmt.convert import relevancy_to_adjust


@pytest.fixture
def mini():
    """ Minimal example """
    return relevancy_to_adjust("distro = fedora: False")

@pytest.fixture
def full():
    """ Full example """
    return relevancy_to_adjust("""
    # feature has been added in Fedora 33
    distro < fedora-33: False

    # using logical operators
    component = firefox && arch = ppc64: False

    arch = s390x: PHASES=novalgrind # modify environment

    # try special operators
    collection contains httpd24 && fips defined: False
    """.replace('    ', ''))

def check(condition, expected):
    """ Check condition against expected """
    adjusted = relevancy_to_adjust(f"{condition}: False")[0]['when']
    assert adjusted == expected


# Valid rules

def test_empty():
    """ Empty relevancy """
    assert relevancy_to_adjust('') == list()

def test_comments(full):
    """ Extract comments """
    assert full[0]['because'] == 'feature has been added in Fedora 33'
    assert full[1]['because'] == 'using logical operators'
    assert full[2]['because'] == 'modify environment'

def test_disable(mini, full):
    """ Disable test """
    assert mini[0]['enabled'] == False
    assert full[0]['enabled'] == False
    assert full[1]['enabled'] == False

def test_environment(full):
    """ Modify environment """
    assert full[2]['environment'] == {'PHASES': 'novalgrind'}

def test_continue(mini):
    """ Explicit continue """
    assert mini[0]['continue'] == False

def test_condition(mini, full):
    """ Expressions conversion """
    assert mini[0]['when'] == 'distro == fedora'
    assert full[0]['when'] == 'distro < fedora-33'
    assert full[1]['when'] == 'component == firefox and arch == ppc64'
    assert full[2]['when'] == 'arch == s390x'
    assert full[3]['when'] == 'collection == httpd24 and fips is defined'

def test_operators_basic():
    """ Basic operators unchanged """
    check('component = python', 'component == python')
    check('component == python', 'component == python')
    check('arch == s390x', 'arch == s390x')
    check('arch != s390x', 'arch != s390x')

def test_operators_distro_name():
    """ Check distro name """
    check('distro = fedora', 'distro == fedora')
    check('distro == fedora', 'distro == fedora')
    check('distro != fedora', 'distro != fedora')

def test_operators_distro_major():
    """ Check distro major version """
    check('distro < fedora-33', 'distro < fedora-33')
    check('distro > fedora-33', 'distro > fedora-33')
    check('distro <= fedora-33', 'distro <= fedora-33')
    check('distro >= fedora-33', 'distro >= fedora-33')

def test_operators_distro_minor():
    """ Check distro minor version """
    check('distro = centos-8.3', 'distro ~= centos-8.3')
    check('distro == centos-8.3', 'distro ~= centos-8.3')
    check('distro != centos-8.3', 'distro ~!= centos-8.3')
    check('distro < centos-8.3', 'distro ~< centos-8.3')
    check('distro > centos-8.3', 'distro ~> centos-8.3')
    check('distro <= centos-8.3', 'distro ~<= centos-8.3')
    check('distro >= centos-8.3', 'distro ~>= centos-8.3')

def test_operators_product():
    """ Special handling for product """
    # rhscl
    check('product = rhscl', 'product == rhscl')
    check('product == rhscl', 'product == rhscl')
    check('product != rhscl', 'product != rhscl')
    # rhscl-3
    check('product < rhscl-3', 'product < rhscl-3')
    check('product > rhscl-3', 'product > rhscl-3')
    check('product <= rhscl-3', 'product <= rhscl-3')
    check('product >= rhscl-3', 'product >= rhscl-3')
    # rhscl-3.3
    check('product < rhscl-3.3', 'product ~< rhscl-3.3')
    check('product > rhscl-3.3', 'product ~> rhscl-3.3')
    check('product <= rhscl-3.3', 'product ~<= rhscl-3.3')
    check('product >= rhscl-3.3', 'product ~>= rhscl-3.3')

def test_operators_special():
    """ Check 'defined' and 'contains' """
    check('fips defined', 'fips is defined')
    check('fips !defined', 'fips is not defined')
    check('collection contains http24', 'collection == http24')
    check('collection !contains http24', 'collection != http24')

def test_not_equal_comma_separated():
    """ Special handling for comma-separated values with != """
    check(
        'distro != centos-7, centos-8',
        'distro != centos-7 and distro != centos-8')

# Invalid rules

def test_invalid_rule():
    """ Invalid relevancy rule """
    with pytest.raises(ConvertError, match='Invalid.*rule'):
        relevancy_to_adjust("weird")

def test_invalid_decision():
    """ Invalid relevancy decision """
    with pytest.raises(ConvertError, match='Invalid.*decision'):
        relevancy_to_adjust("distro < fedora-33: weird")

def test_invalid_expression():
    """ Invalid relevancy expression """
    with pytest.raises(ConvertError, match='Invalid.*expression'):
        relevancy_to_adjust("distro * fedora-33: False")

def test_invalid_operator():
    """ Invalid relevancy operator """
    with pytest.raises(ConvertError, match='Invalid.*operator'):
        relevancy_to_adjust("distro <> fedora-33: False")
