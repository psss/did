# coding: utf-8

import os
import shutil
import tempfile

import click.testing
import jsonschema
import pytest

import tmt
import tmt.cli
from tmt.base import Link
from tmt.utils import SpecificationError

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
    test = tmt.Test.from_dict(dict(test='./test.sh'), '/smoke')
    assert test.name == '/smoke'
    assert test.component == list()
    assert test.test == './test.sh'
    assert test.path == '/'
    assert test.require == list()
    assert test.environment == dict()
    assert test.duration == '5m'
    assert test.enabled is True
    assert test.result == 'respect'
    assert test.tag == list()


def test_test_invalid():
    """ Test invalid test """
    # Missing name
    with pytest.raises(tmt.utils.GeneralError):
        tmt.Test.from_dict({}, '')
    # Invalid name
    with pytest.raises(SpecificationError):
        tmt.Test.from_dict({}, 'bad')
    # Invalid attributes
    for key in ['component', 'require', 'tag']:
        with pytest.raises(SpecificationError) as exc_context:
            tmt.Test.from_dict({key: 1}, '/smoke', raise_on_validation_error=True)

        exc = exc_context.value

        assert isinstance(exc, SpecificationError)
        assert exc.args[0] \
            == 'fmf node /smoke failed validation'

        validation_error, error_message = exc.validation_errors[0]

        assert isinstance(validation_error, jsonschema.ValidationError)
        assert error_message \
            == f'/smoke:{key} - 1 is not valid under any of the given schemas'

    with pytest.raises(SpecificationError):
        tmt.Test.from_dict({'environment': 'string'}, '/smoke', raise_on_validation_error=True)
    # Listify attributes
    assert tmt.Test.from_dict({'test': 'test', 'tag': 'a'}, '/smoke').tag == ['a']
    assert tmt.Test.from_dict({'test': 'test', 'tag': ['a', 'b']}, '/smoke').tag == ['a', 'b']


def test_link():
    """ Test the link attribute parsing """
    # No link should default to an empty list
    assert Link().get() == []

    # Single string (default relation)
    assert Link('/fmf/id').get() == [dict(relates='/fmf/id')]
    # Multiple strings (default relation)
    assert Link(['one', 'two']).get() == [
        dict(relates='one'), dict(relates='two')]
    # Multiple string mixed relation
    assert Link(['implicit', dict(duplicates='explicit')]).get() == [
        dict(relates='implicit'), dict(duplicates='explicit')]
    # Multiple strings (explicit relation)
    family = [dict(parent='mon'), dict(child='son')]
    assert Link(family).get() == family

    # Single dictionary (default relation)
    assert Link(dict(name='foo')).get() == [dict(relates=dict(name='foo'))]
    # Single dictionary (explicit relation)
    assert Link(dict(verifies='foo')).get() == [dict(verifies='foo')]
    # Multiple dictionaries
    family = [dict(parent='mom', note='foo'), dict(child='son')]
    assert Link(family).get() == family

    # Selected relations
    assert Link(family).get('parent') == [dict(parent='mom', note='foo')]
    assert Link(family).get('child') == [dict(child='son')]

    # Full fmf id
    fmf_id = tmt.utils.yaml_to_dict("""
        blocked-by:
            url: https://github.com/teemtee/fmf
            name: /stories/select/filter/regexp
        note: Need to get the regexp filter working first.
        """)
    link = Link(fmf_id)
    assert link.get() == [fmf_id]

    # Invalid links and relations
    with pytest.raises(SpecificationError, match='Invalid link'):
        Link(123)
    with pytest.raises(SpecificationError, match='Multiple relations'):
        Link(dict(verifies='one', blocks='another'))
    with pytest.raises(SpecificationError, match='Invalid link relation'):
        Link(dict(depends='other'))
    with pytest.raises(SpecificationError, match='Unexpected link key'):
        Link(dict(verifies='story', url='https://example.org', ref='devel'))
