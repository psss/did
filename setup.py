#!/usr/bin/env python
# coding: utf-8

import re
from io import open
from setuptools import setup

# Parse the version and release from the spec file
with open('tmt.spec', encoding='utf-8') as specfile:
    lines = "\n".join(line.rstrip() for line in specfile)
    version = re.search('Version: (.+)', lines).group(1).rstrip()
    release = re.search('Release: (\d+)', lines).group(1).rstrip()

# acceptable version schema: major.minor[.patch][sub]
__version__ = '.'.join([version, release])
__pkg__ = 'tmt'
__pkgdir__ = {}
__pkgs__ = [
    'tmt',
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
    'fmf>=0.9.2',
    'click',
    'requests',
]
extras_require = {
    'docs': ['sphinx', 'sphinx_rtd_theme', 'mock'],
    'tests': ['pytest', 'python-coveralls', 'mock'],
    'provision': ['testcloud'],
    'convert': ['nitrate'],
    'report-html': ['jinja2'],
}
extras_require['all'] = [dependency
    for extra in extras_require.values()
    for dependency in extra]

pip_src = 'https://pypi.python.org/packages/source'
__deplinks__ = []

# README is in the parent directory
readme = 'README.rst'
with open(readme, encoding='utf-8') as _file:
    readme = _file.read()

github = 'https://github.com/psss/tmt'
download_url = '{0}/archive/master.zip'.format(github)

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
    package_data = {
        'tmt/steps/execute': ['run.sh']},
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Utilities',
    ],
    keywords=['metadata', 'testing'],
    dependency_links=__deplinks__,
    description=__desc__,
    install_requires=install_requires,
    extras_require=extras_require,
    name=__pkg__,
    package_dir=__pkgdir__,
    packages=__pkgs__,
    provides=__provides__,
    scripts=__scripts__,
    version=__version__,
)

setup(**default_setup)
