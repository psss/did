#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

import re
from setuptools import setup

# Parse the version and release from master spec file
# RPM spec file is in the parent directory
spec_pth = 'status-report.spec'
with open(spec_pth) as f:
    lines = "\n".join(l.rstrip() for l in f)
    version = re.search('Version: (.+)', lines).group(1).rstrip()
    release = re.search('Release: (\d+)', lines).group(1).rstrip()

# acceptable version schema: major.minor[.patch][sub]
__version__ = '.'.join([version, release])
__pkg__ = 'status_report'
__pkgdir__ = {'status_report': 'source/status_report'}
__pkgs__ = [
    'status_report',
    'status_report.plugins',
]
__provides__ = ['status_report']
__desc__ = 'Status Report - Comfortable CLI Activity Status Reporting'
__scripts__ = ['source/status-report']
__irequires__ = [
    'python_dateutil==2.4.2',
    'sqlalchemy==1.0.0',
    'kerberos==1.2.2',  # not python 3 compatible!
    'urllib2_kerberos==0.1.6',  # not python 3 compatible!
]
pip_src = 'https://pypi.python.org/packages/source'
__deplinks__ = []

# README is in the parent directory
readme_pth = 'README.rst'
with open(readme_pth) as _file:
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
    keywords=['information', 'postgresql', 'tasks'],
    dependency_links=__deplinks__,
    description=__desc__,
    install_requires=__irequires__,
    name=__pkg__,
    package_dir=__pkgdir__,
    packages=__pkgs__,
    provides=__provides__,
    scripts=__scripts__,
    version=__version__,
    zip_safe=False,  # we reference __file__; see [1]
)

setup(**default_setup)
