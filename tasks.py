#!/usr/bin/env python
# coding: utf-8
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import absolute_import, unicode_literals

import os

from invoke import task, run

try:
    from did.utils import log, LOG_INFO
except Exception as e:
    import logging
    LOG_INFO = logging.INFO
    log = logging.getLogger()

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


_bob_py_file_help = {
    'name': "Name of the python file",
    'answers': "path to mrbob.ini with [variables] defined",
    # FIXME: Add remaining bob_py_file_help strings
}


# FIXME: make 'bob' stuff reusable? redefining code here
# and in the other bob func below... not good.
@task(help=_bob_py_file_help)
def bob_py_file(path='./', answers='~/.mrbob.ini', overwrite=False):
    '''
    MrBob: New .py File
    -------------------

    Note: MrBob asks for filename rather than pass it here to the task
    to make it more easily accessible from the template

    '''
    log.info("MrBob is building a .py file")

    template = 'bobtemplates/py_file'

    path = path or './'
    answers = answers or os.path.expanduser('~/.mrbob.ini')

    cmd = 'mrbob {} -O {}'.format(template, path)
    if answers:
        cmd += ' -c {}'.format(answers)

    log.info(" ... Defaults: {}".format(answers))
    run(cmd, pty=True)


@task
def bob_did_plugin(path=None, answers=None, overwrite=False):
    '''
    MrBob: New did Plugin
    ---------------------

    Create all the files needed to start writing a new did plugin.

    Note: MrBob asks for filename rather than pass it here to the task
    to make it more easily accessible from the template

    '''
    log.info("MrBob is building a did plugin template")

    template = 'bobtemplates/plugin'

    path = path or './did/plugins'

    cmd = 'mrbob {} -O {}'.format(template, path)

    if answers:
        if not os.path.exists(answers):
            # if the path doesn't exist, don't try to load it
            raise RuntimeError('{} does not exist'.format(answers))
        cmd += ' -c {}'.format(answers)

    log.info(" ... Defaults: {}".format(answers))
    run(cmd, pty=True)
