import pytest
import shutil

import tmt
import tmt.beakerlib


@pytest.mark.web
def test_library():
    """ Fetch a beakerlib library with/without providing a parent """
    parent = tmt.utils.Common(workdir=True)
    library_with_parent = tmt.beakerlib.Library(
        'library(openssl/certgen)', parent=parent)
    library_without_parent = tmt.beakerlib.Library(
        'library(openssl/certgen)')

    for library in [library_with_parent, library_without_parent]:
        assert library.format == 'rpm'
        assert library.repo == 'openssl'
        assert library.url == 'https://github.com/beakerlib/openssl'
        assert library.ref == 'master'
        assert library.dest == tmt.beakerlib.DEFAULT_DESTINATION
        shutil.rmtree(library.parent.workdir)


@pytest.mark.web
def test_dependencies():
    """ Check requires for possible libraries """
    parent = tmt.utils.Common(workdir=True)
    requires, recommends, libraries = tmt.beakerlib.dependencies(
        ['library(httpd/http)', 'wget'], ['forest'], parent=parent)
    # Check for correct requires and recommends
    for require in ['httpd', 'lsof', 'mod_ssl']:
        assert require in requires
        assert require in libraries[0].require
    assert 'openssl' in libraries[1].require
    assert 'forest' in recommends
    assert 'wget' in requires
    # Library require should be in httpd requires but not in the final result
    assert 'library(openssl/certgen)' in libraries[0].require
    assert 'library(openssl/certgen)' not in requires
    # Check library attributes for sane values
    assert libraries[0].repo == 'httpd'
    assert libraries[0].name == '/http'
    assert libraries[0].url == 'https://github.com/beakerlib/httpd'
    assert libraries[0].ref == 'master'
    assert libraries[0].dest == tmt.beakerlib.DEFAULT_DESTINATION
    assert libraries[1].repo == 'openssl'
    assert libraries[1].name == '/certgen'
    shutil.rmtree(parent.workdir)
