import shutil

import pytest

import tmt
import tmt.base
import tmt.beakerlib


@pytest.mark.web
def test_library():
    """ Fetch a beakerlib library with/without providing a parent """
    parent = tmt.utils.Common(workdir=True)
    library_with_parent = tmt.beakerlib.Library(
        identifier=tmt.base.RequireSimple('library(openssl/certgen)'), parent=parent)
    library_without_parent = tmt.beakerlib.Library(
        identifier=tmt.base.RequireSimple('library(openssl/certgen)'))

    for library in [library_with_parent, library_without_parent]:
        assert library.format == 'rpm'
        assert library.repo == 'openssl'
        assert library.url == 'https://github.com/beakerlib/openssl'
        assert library.ref == 'master'  # The default branch is master
        assert library.dest == tmt.beakerlib.DEFAULT_DESTINATION
        shutil.rmtree(library.parent.workdir)


@pytest.mark.web
@pytest.mark.parametrize(
    'url, name, default_branch', [
        ('https://github.com/beakerlib/httpd', '/http', 'master'),
        ('https://github.com/beakerlib/example', '/file', 'main')
        ])
def test_library_from_fmf(url, name, default_branch):
    """ Fetch beakerlib library referenced by fmf identifier """
    library = tmt.beakerlib.Library(identifier=tmt.base.RequireFmfId(url=url, name=name))
    assert library.format == 'fmf'
    assert library.ref == default_branch
    assert library.url == url
    assert library.dest == tmt.beakerlib.DEFAULT_DESTINATION
    assert library.repo == url.split('/')[-1]
    assert library.name == name
    shutil.rmtree(library.parent.workdir)


@pytest.mark.web
def test_invalid_url_conflict():
    """ Saner check if url mismatched for translated library """
    parent = tmt.utils.Common(workdir=True)
    # Fetch to cache 'tmt' repo
    tmt.beakerlib.Library(
        identifier=tmt.base.RequireFmfId(
            url='https://github.com/teemtee/tmt',
            name='/',
            path='/tests/libraries/local/data'),
        parent=parent)
    # Library 'tmt' repo is already fetched from different git,
    # however upstream (gh.com/beakerlib/tmt) repo does not exist,
    # so there can't be "already fetched" error
    with pytest.raises(tmt.beakerlib.LibraryError):
        tmt.beakerlib.Library(identifier='library(tmt/foo)', parent=parent)
    shutil.rmtree(parent.workdir)


@pytest.mark.web
def test_dependencies():
    """ Check requires for possible libraries """
    parent = tmt.utils.Common(workdir=True)
    requires, recommends, libraries = tmt.beakerlib.dependencies(
        [tmt.base.RequireSimple('library(httpd/http)'), tmt.base.RequireSimple('wget')],
        [tmt.base.RequireSimple('forest')],
        parent=parent)
    # Check for correct requires and recommends
    for require in ['httpd', 'lsof', 'mod_ssl']:
        assert require in requires
        assert require in libraries[0].require
    assert 'openssl' in libraries[2].require
    assert 'forest' in recommends
    assert 'wget' in requires
    # Library require should be in httpd requires but not in the final result
    assert 'library(openssl/certgen)' in libraries[0].require
    assert 'library(openssl/certgen)' not in requires
    # Check library attributes for sane values
    assert libraries[0].repo == 'httpd'
    assert libraries[0].name == '/http'
    assert libraries[0].url == 'https://github.com/beakerlib/httpd'
    assert libraries[0].ref == 'master'  # The default branch is master
    assert libraries[0].dest == tmt.beakerlib.DEFAULT_DESTINATION
    assert libraries[1].repo == 'openssl'
    assert libraries[1].name == '/certgen'
    shutil.rmtree(parent.workdir)
