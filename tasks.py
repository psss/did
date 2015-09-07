#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import absolute_import, unicode_literals

import os

from invoke import task, run

try:
    from did.utils import Logging, LOG_INFO
    _logging = Logging('did.tasks')
    log = _logging.logger
except Exception as e:
    import logging
    LOG_INFO = logging.INFO
    log = logging.getLogger('did.tasks')

# set log level to INFO
log.setLevel(LOG_INFO)


@task
def build(sdist=False, rpm=False):
    '''
    Build Packages
    --------------

    Supports

     * sdist
     * rpm [fedora]

    '''
    log.info("Running build command!")
    if sdist:
        run("python setup.py sdist")
    if rpm:
        run("make rpm")
    return


@task
def pytest():
    '''
    Run pytest
    ----------
    '''
    log.info("Running `{}` command!".format(__name__))
    run("py.test tests/")
    return


@task
def coverage(report=True, coveralls=False, append=True):
    '''
    Run Coverage Test [pytest]
    --------------------------

    Supports
     * coverage [reporting, coveralls, append]
     * coveralls

    Do not support (yet)
     * coverage [xml]
    '''
    log.info("Running `{}` command!".format(__name__))
    opts = {}
    # save to new timestamped file in ~/.coverage ?
    _cmd = "coverage run {run_opts}--source=did -m py.test tests"

    opts['run_opts'] = '--append ' if append else ''
    cmd = _cmd.format(**opts)

    log.info(" ... Options: {}".format(opts))
    run(cmd)
    if coveralls:
        run("coveralls")
    if report:
        run("coverage report")
    return


@task
def docs(html=False):
    '''
    Build Documentation
    -------------------

    '''
    log.info("Running Documentation command!")
    _cmd = "cd docs;"
    if html:
        cmd = "{0} make html".format(_cmd)
    else:
        cmd = "{0} make html".format(_cmd)
    run(cmd)
    return


@task
def clean_git(force=False, options='Xd'):
    '''
    Clean Your Repo
    ---------------

    '''
    log.info("Running Git Repository Clean command")
    force = 'f' if force else 'n'
    cmd = "git clean"
    if options:
        _options = ' -{}{}'.format(options, force)
        cmd += _options
    log.info(" ... Options: {}".format(_options))
    run(cmd)


@task
def bob_py_file(name, template=None, overwrite=False):
    '''
    MrBob: New .py File
    -------------------

    '''
    log.info("Bob is building a .py file")

    template = template or 'bobstemplates/default.py'
    name = name.strip()
    if not name.startswith('/'):
        name = './' + name
    if not overwrite and os.path.exists(name):
        raise RuntimeError('{} exists!'.format(name))

    print name
