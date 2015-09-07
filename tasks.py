#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import absolute_import, unicode_literals

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
    Build
    -----

    '''
    log.info("Running build command!")
    if sdist:
        run("python setup.py sdist")
    if rpm:
        run("make rpm")


@task
def test(coverage=False):
    '''
    Test
    ----

    '''
    log.info("Running Test command!")
    if coverage:
        log.info(" ... Running Coverage!")
        run("coverage run --source=did -m py.test tests")
    else:
        run("py.test tests/")


@task
def docs(html=False):
    '''
    Test
    ----

    '''
    log.info("Running Documentation command!")
    _cmd = "cd docs;"
    if html:
        cmd = "{0} make html".format(_cmd)
    else:
        cmd = "{0} make html".format(_cmd)
    run(cmd)


@task
def clean_git(force=False, options='Xd'):
    '''
    Test
    ----

    '''
    log.info("Running Git Repository Clean command")
    force = 'f' if force else 'n'
    cmd = "git clean"
    if options:
        _options = ' -{}{}'.format(options, force)
        cmd += _options
    log.info(" ... Options: {}".format(_options))
    run(cmd)
