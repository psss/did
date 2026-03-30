#!/usr/bin/env python

import re

from setuptools import setup

# Parse version and release from the spec file
with open('did.spec', encoding="utf-8") as specfile:
    # pylint: disable=invalid-name
    lines = "\n".join(line.rstrip() for line in specfile)
    version_match = re.search('Version: (.+)', lines)
    release_match = re.search('Release: (\\d+)', lines)
    if version_match is None or release_match is None:
        raise ValueError("Could not find Version or Release in did.spec file")
    version = version_match.group(1).rstrip()
    release = release_match.group(1).rstrip()
VERSION = '.'.join([version, release])

# Prepare install requires and extra requires
install_requires = [
    'python_dateutil',
    'requests',
    'requests-gssapi',
    'tenacity',
    'urllib3'
    ]
extras_require = {
    'bodhi': ['bodhi-client'],
    'bugzilla': ['python-bugzilla'],
    'docs': ['sphinx==8.2.3', 'sphinx-rtd-theme==3.0.2'],
    'google': ['google-api-python-client', 'google-auth-oauthlib'],
    'jira': ['requests_gssapi'],
    'koji': ['koji'],
    'redmine': ['feedparser'],
    'nitrate': ['nitrate'],
    'rt': ['gssapi'],
    'tests': ['pytest', 'pytest-xdist', 'pytest-cov', 'python-coveralls', 'pre-commit',
              'setuptools'],
    'mypy': ['types-setuptools', 'types-python-dateutil', 'lxml',
             'types-requests', 'types-urllib3', 'types-httplib2'],
    }
extras_require['all'] = [
    dependency
    for extra in extras_require.values()
    for dependency in extra]

# Prepare the long description from readme
with open('README.rst', encoding="utf-8") as readme:
    description = readme.read()

setup(
    name='did',
    description='did - What did you do last week, month, year?',
    long_description=description,
    url='https://github.com/psss/did',
    download_url='https://github.com/psss/did/archive/master.zip',

    version=VERSION,
    provides=['did'],
    packages=['did', 'did.plugins'],
    scripts=['bin/did'],
    install_requires=install_requires,
    extras_require=extras_require,

    author='Petr Šplíchal',
    author_email='psplicha@redhat.com',
    maintainer='Petr Šplíchal',
    maintainer_email='psplicha@redhat.com',
    license='GPL-2.0-or-later',

    keywords=['status', 'report', 'tasks', 'work'],
    classifiers=[
        'Natural Language :: English',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Topic :: Office/Business',
        'Topic :: Utilities',
        ],

    data_files=[],
    dependency_links=[],
    package_dir={},
    zip_safe=False,
    )
