# coding: utf-8

import os
import pytest
import shutil
import tempfile
import click.testing

import tmt
import tmt.cli

runner = click.testing.CliRunner()

def test_invalid_yaml_syntax():
    """ Invalid yaml syntax """
    tmp = tempfile.mkdtemp()
    original_directory = os.getcwd()
    os.chdir(tmp)
    result = runner.invoke(tmt.cli.main, ['init', '--template', 'mini'])
    with open('plans/example.fmf', 'a') as plan:
        plan.write('bad line')
    result = runner.invoke(tmt.cli.main)
    assert isinstance(result.exception, tmt.utils.GeneralError)
    assert result.exit_code != 0
    os.chdir(original_directory)
    shutil.rmtree(tmp)

def test_test_defaults():
    """ Test default test attributes """
    test = tmt.Test(dict(test='./test.sh'), name='/smoke')
    assert test.name == '/smoke'
    assert test.component == list()
    assert test.test == './test.sh'
    assert test.path == '/'
    assert test.require == list()
    assert test.environment == dict()
    assert test.duration == '5m'
    assert test.enabled == True
    assert test.result == 'respect'
    assert test.tag == list()

def test_test_invalid():
    """ Test invalid test """
    # Missing name
    with pytest.raises(tmt.utils.GeneralError):
        test = tmt.Test({})
    # Invalid name
    with pytest.raises(tmt.utils.SpecificationError):
        test = tmt.Test({}, name='bad')
    # Invalid attributes
    for key in ['component', 'require', 'tag']:
        with pytest.raises(tmt.utils.SpecificationError):
            test = tmt.Test({key: 1}, name='/smoke')
    with pytest.raises(tmt.utils.SpecificationError):
        test = tmt.Test({'environment': 'string'}, name='/smoke')
    # Listify attributes
    assert tmt.Test({'tag': 'a'}, name='/smoke').tag == ['a']
    assert tmt.Test({'tag': ['a', 'b']}, name='/smoke').tag == ['a', 'b']
