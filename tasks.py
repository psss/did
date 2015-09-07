#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: "Chris Ward" <cward@redhat.com>

from __future__ import absolute_import, unicode_literals

from invoke import task, run

from did.utils import log, LOG_INFO

# set log level to INFO
log.setLevel(LOG_INFO)


@task
def build(sdist=False, rpm=False):
    log.info("Running build command!")
    if sdist:
        run("python setup.py sdist")
    if rpm:
        run("make rpm")
