# coding: utf-8

import os
import shutil
import tempfile

import click.testing
import jsonschema
import pytest

import tmt
import tmt.cli
from tmt.base import FmfId, Link, LinkNeedle, Links
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
        assert exc.message == 'fmf node /smoke failed validation'

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
    assert Links().get() == []

    # Single string (default relation)
    assert Links(data='/fmf/id').get() == [Link(relation='relates', target='/fmf/id')]
    # Multiple strings (default relation)
    assert Links(data=['one', 'two']).get() == [
        Link(relation='relates', target='one'), Link(relation='relates', target='two')]
    # Multiple string mixed relation
    assert Links(data=['implicit', dict(duplicates='explicit')]).get() == [
        Link(relation='relates', target='implicit'),
        Link(relation='duplicates', target='explicit')]
    # Multiple strings (explicit relation)
    assert Links(data=[dict(parent='mom'), dict(child='son')]).get() == [
        Link(relation='parent', target='mom'), Link(relation='child', target='son')]

    # Single dictionary (default relation)
    assert Links(data=dict(name='foo')).get() == [
        Link(relation='relates', target=FmfId(name='foo'))]
    # Single dictionary (explicit relation)
    assert Links(data=dict(verifies='foo')).get() == [Link(relation='verifies', target='foo')]
    # Multiple dictionaries
    family = [dict(parent='mom', note='foo'), dict(child='son')]
    assert Links(data=family).get() == [
        Link(relation='parent', target='mom', note='foo'), Link(relation='child', target='son')
        ]

    # Selected relations
    assert Links(data=family).get('parent') == [Link(relation='parent', target='mom', note='foo')]
    assert Links(data=family).get('child') == [Link(relation='child', target='son')]

    # Full fmf id
    fmf_id = tmt.utils.yaml_to_dict("""
        blocked-by:
            url: https://github.com/teemtee/fmf
            name: /stories/select/filter/regexp
        note: Need to get the regexp filter working first.
        """)
    link = Links(data=fmf_id)
    assert link.get() == [
        Link(
            relation='blocked-by',
            target=FmfId(
                url=fmf_id['blocked-by']['url'],
                name=fmf_id['blocked-by']['name']),
            note=fmf_id['note'])]

    # Invalid links and relations
    with pytest.raises(SpecificationError, match='Invalid link'):
        Links(data=123)
    with pytest.raises(SpecificationError, match='Multiple relations'):
        Links(data=dict(verifies='one', blocks='another'))
    with pytest.raises(SpecificationError, match='Invalid link relation'):
        Links(data=dict(depends='other'))

    # Searching for links
    links = Links(data=[dict(parent='mom', note='foo'), dict(child='son', note='bar')])
    assert links.has_link(LinkNeedle())
    assert links.has_link(LinkNeedle(relation='[a-z]+'))
    assert links.has_link(LinkNeedle(relation='en'))
    assert links.has_link(LinkNeedle(target='^mom$'))
    assert links.has_link(LinkNeedle(target='on'))
    assert not links.has_link(LinkNeedle(relation='verifies', target='son'))
    assert not links.has_link(LinkNeedle(relation='parent', target='son'))
