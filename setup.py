#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from setuptools import setup

# acceptable version schema: major.minor[.patch][sub]
__version__ = '0.1.1'
__pkg__ = 'status_report'
__pkgdir__ = {'status_report': 'source/status_report'}
__pkgs__ = [
    'status_report',
    'status_report.plugins',
]
__provides__ = ['status_report']
__desc__ = 'Status Report - Comfortable CLI Activity Status Reporting'
__scripts__ = ['source/status-report']
__requires__ = [
    'python_dateutil',
    'kerberos',
]
__irequires__ = [
    'python_dateutil',
    'kerberos',
]
pip_src = 'https://pypi.python.org/packages/source'
__deplinks__ = []

with open('README') as _file:
    readme = _file.read()

github = 'https://github.com/psss/status-report'
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
    name=__pkg__,
    package_dir=__pkgdir__,
    packages=__pkgs__,
    provides=__provides__,
    requires=__requires__,
    scripts=__scripts__,
    version=__version__,
    zip_safe=False,  # we reference __file__; see [1]
)

setup(**default_setup)
