#!/usr/bin/env python
# coding: utf-8

import re
from setuptools import setup

# Parse version and release from the spec file
with open('did.spec') as specfile:
    lines = "\n".join(line.rstrip() for line in specfile)
    version = re.search('Version: (.+)', lines).group(1).rstrip()
    release = re.search('Release: (\d+)', lines).group(1).rstrip()
version = '.'.join([version, release])

# Prepare install requires and extra requires
install_requires = [
    'python_dateutil',
    'requests',
    'gssapi',
    ]
extras_require = {
    'bitly': ['bitly_api'],
    'bugzilla': ['python-bugzilla'],
    'docs': ['sphinx', 'mock', 'sphinx_rtd_theme'],
    'google': ['google-api-python-client', 'oauth2client'],
    'jira': ['requests_gssapi'],
    'redmine': ['feedparser'],
    'tests': ['pytest', 'python-coveralls'],
    }
extras_require['all'] = [dependency
    for extra in extras_require.itervalues()
    for dependency in extra]

# Prepare the long description from readme
with open('README.rst') as readme:
    description = readme.read()

setup(
    name='did',
    description='did - What did you do last week, month, year?',
    long_description=readme,
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
    license='GPLv3',

    keywords=['status', 'report', 'tasks', 'work'],
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Topic :: Office/Business',
        'Topic :: Utilities',
    ],

    data_files=[],
    dependency_links=[],
    package_dir={},
    zip_safe=False,
)
