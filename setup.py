#!/usr/bin/env python
# coding: utf-8

import re

from setuptools import setup

# Parse version and release from the spec file
with open('did.spec') as specfile:
    lines = "\n".join(line.rstrip() for line in specfile)
    version = re.search('Version: (.+)', lines).group(1).rstrip()
    release = re.search('Release: (\\d+)', lines).group(1).rstrip()
version = '.'.join([version, release])

# Prepare install requires and extra requires
install_requires = [
    'python_dateutil',
    'requests',
    ]
extras_require = {
    'bodhi': ['bodhi-client'],
    'bugzilla': ['python-bugzilla'],
    'docs': ['sphinx>3', 'mock', 'sphinx_rtd_theme'],
    'google': ['google-api-python-client', 'oauth2client'],
    'jira': ['requests_gssapi'],
    'koji': ['koji'],
    'redmine': ['feedparser'],
    'rt': ['gssapi'],
    'tests': ['pytest', 'python-coveralls', 'pre-commit'],
    }
extras_require['all'] = [
    dependency
    for extra in extras_require.values()
    for dependency in extra]

# Prepare the long description from readme
with open('README.rst') as readme:
    description = readme.read()

setup(
    name='did',
    description='did - What did you do last week, month, year?',
    long_description=description,
    url='https://github.com/psss/did',
    download_url='https://github.com/psss/did/archive/master.zip',

    version=version,
    provides=['did'],
    packages=['did', 'did.plugins'],
    scripts=['bin/did'],
    install_requires=install_requires,
    extras_require=extras_require,

    author='Petr Šplíchal',
    author_email='psplicha@redhat.com',
    maintainer='Petr Šplíchal',
    maintainer_email='psplicha@redhat.com',
    license='GPLv2+',

    keywords=['status', 'report', 'tasks', 'work'],
    classifiers=[
        'License :: OSI Approved :: '
            'GNU General Public License v2 or later (GPLv2+)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Office/Business',
        'Topic :: Utilities',
        ],

    data_files=[],
    dependency_links=[],
    package_dir={},
    zip_safe=False,
    )
