#!/usr/bin/env python
# coding: utf-8

import re
import sys
from io import open

from setuptools import setup

# Parse version from the spec file
with open('tmt.spec', encoding='utf-8') as specfile:
    lines = "\n".join(line.rstrip() for line in specfile)
    version = re.search('Version: (.+)', lines).group(1).rstrip()

# acceptable version schema: major.minor[.patch][sub]
__version__ = version
__pkg__ = 'tmt'
__pkgdata__ = {
    'tmt': [
        'schemas/*.yaml',
        'schemas/*/*.yaml',
        'steps/execute/scripts/*',
        'steps/report/html/*'
        ]
}
__pkgdir__ = {}
__pkgs__ = [
    'tmt',
    'tmt/plugins',
    'tmt/steps',
    'tmt/steps/discover',
    'tmt/steps/provision',
    'tmt/steps/prepare',
    'tmt/steps/execute',
    'tmt/steps/report',
    'tmt/steps/finish',
    ]
__provides__ = ['tmt']
__desc__ = 'Test Management Tool'
__scripts__ = ['bin/tmt']

# Prepare install requires and extra requires
install_requires = [
    'fmf>=1.2.1',
    'click',
    'requests',
    'ruamel.yaml',
    ]

# typing_extensions is needed with Python 3.7 and older, types imported
# from that package (Literal, Protocol, TypedDict, ...) become available
# from typing since Python 3.8.
install_requires.append("typing-extensions>=3.7.4.3; python_version < '3.8'")

# dataclasses is needed with Python 3.6
install_requires.append("dataclasses; python_version < '3.7'")

# entry_points is part of Python 3.9+
install_requires.append("importlib_metadata; python_version < '3.9'")

extras_require = {
    'docs': [
        'sphinx>=3',
        'sphinx_rtd_theme'],
    'tests': [
        'flake8',
        'pytest',
        'python-coveralls',
        'requre',
        'pre-commit',
        'mypy'
        ],
    'provision': ['testcloud>=0.8.1'],
    'convert': [
        'nitrate',
        'markdown',
        'python-bugzilla',
        'html2text'],
    'report-html': ['jinja2'],
    'report-junit': ['junit_xml'],
    'report-polarion': ['junit_xml', 'pylero'],
    'export-polarion': ['pylero'],
}
extras_require['all'] = [
    dependency
    for extra in extras_require.values()
    for dependency in extra]

pip_src = 'https://pypi.python.org/packages/source'
__deplinks__ = []

# README is in the parent directory
readme = 'README.rst'
with open(readme, encoding='utf-8') as _file:
    readme = _file.read()

github = 'https://github.com/teemtee/tmt'
download_url = '{0}/archive/main.zip'.format(github)

default_setup = dict(
    url=github,
    license='MIT',
    author='Petr Splichal',
    author_email='psplicha@redhat.com',
    maintainer='Petr Splichal',
    maintainer_email='psplicha@redhat.com',
    download_url=download_url,
    long_description=readme,
    data_files=[],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Utilities',
        ],
    keywords=['metadata', 'testing'],
    dependency_links=__deplinks__,
    description=__desc__,
    install_requires=install_requires,
    extras_require=extras_require,
    name=__pkg__,
    package_data=__pkgdata__,
    package_dir=__pkgdir__,
    packages=__pkgs__,
    provides=__provides__,
    scripts=__scripts__,
    version=__version__,
    )

setup(**default_setup)
