#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

import re
from setuptools import setup

# Parse the version and release from master spec file
# RPM spec file is in the parent directory
spec_pth = 'did.spec'
with open(spec_pth) as f:
    lines = "\n".join(l.rstrip() for l in f)
    version = re.search('Version: (.+)', lines).group(1).rstrip()
    release = re.search('Release: (\d+)', lines).group(1).rstrip()

# acceptable version schema: major.minor[.patch][sub]
__version__ = '.'.join([version, release])
__pkg__ = 'did'
__pkgdir__ = {}
__pkgs__ = [
    'did',
    'did.plugins',
]
__provides__ = ['did']
__desc__ = 'did - What did you do last week, month, year?'
__scripts__ = ['bin/did']
__irequires__ = [
    'python_dateutil==2.4.2',
    'urllib2_kerberos',
    'python-bugzilla',  # FIXME: make optional? see __xrequires__
    'pykerberos',
]
__xrequires__ = {
    # `install` usage: pip install did[tests,docs]
    # `develop` usage: python setup.py -e .[tests,docs]
    'tests': [
        'pytest==2.7.2',
    ],
    'docs': [
        'sphinx==1.3.1',
    ],
    'bootstrap': [
        'sphinx_bootstrap_theme',
    ],
    'bitly': [
        'bitly_api',
    ],
}

pip_src = 'https://pypi.python.org/packages/source'
__deplinks__ = []

# README is in the parent directory
readme_pth = 'README.rst'
with open(readme_pth) as _file:
    readme = _file.read()

github = 'https://github.com/psss/did'
download_url = '%s/archive/master.zip' % github

default_setup = dict(
    url=github,
    license='GPLv2',
    author='Petr Splichal',
    author_email='psplicha@redhat.com',
    maintainer='Chris Ward',
    maintainer_email='cward@redhat.com',
    download_url=download_url,
    long_description=readme,
    data_files=[],
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Topic :: Office/Business',
        'Topic :: Utilities',
    ],
    keywords=['information', 'postgresql', 'tasks', 'snippets'],
    dependency_links=__deplinks__,
    description=__desc__,
    install_requires=__irequires__,
    extras_require=__xrequires__,
    name=__pkg__,
    package_dir=__pkgdir__,
    packages=__pkgs__,
    provides=__provides__,
    scripts=__scripts__,
    version=__version__,
    zip_safe=False,  # we reference __file__; see [1]
)

setup(**default_setup)
