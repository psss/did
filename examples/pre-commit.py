#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   status-report - Generate status report stats
#   Author: Petr Šplíchal <psplicha@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2012 Red Hat, Inc. All rights reserved.
#
#   This copyrighted material is made available to anyone wishing
#   to use, modify, copy, or redistribute it subject to the terms
#   and conditions of the GNU General Public License version 2.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE. See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public
#   License along with this program; if not, write to the Free
#   Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
#   Boston, MA 02110-1301, USA.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
Git pre-commit hooks for stats-report.
"""

import argparse
import sys
import subprocess
from status_report.utils import log, LOG_DEBUG

# Turn on DEBUG so we can get a full log on each commit
log.setLevel(LOG_DEBUG)


def run(cmd):
    cmd = cmd if isinstance(cmd, list) else cmd.split()
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as error:
        log.error("'{0}' failed: {1}".format(cmd, error))
        raise
    output, errors = process.communicate()
    if process.returncode != 0 or errors:
        if output:
            log.error(output)
        if errors:
            log.error(errors)
        sys.exit(process.returncode)
    return output, errors


def run_tests():
    '''
    Run all the available tests.
    '''
    # Try to run make build
    cmd = "py.test source/tests"
    return run(cmd)


def make_rpm():
    '''
    Make sure we haven't broken the rpm source builds
    '''
    # Try to run make build
    cmd = 'make build'
    return run(cmd)


def main():
    """ Main function handling configuration files etc """
    parser = argparse.ArgumentParser(
        description='Git python commit hooks')
    parser.add_argument(
        '--make-rpm', action='store_const', const=True, default=True,
        help='Build RPMs from source')
    parser.add_argument(
        '--run-tests', action='store_const', const=True, default=True,
        help='Run all available tests')
    parser.add_argument(
        '--stash-first', action='store_const', const=True, default=False,
        help='Run all available tests')
    args = parser.parse_args()

    # make sure we're working with only the staged content!
    if args.stash_first:
        run('git stash -q --keep-index')

    try:
        results = []
        if args.make_rpm:
            log.debug('RPM Build: START')
            results.append({'make_rpm': make_rpm()})
            log.warn('RPM Build: PASS')
        if args.run_tests:
            log.debug('TESTS RUN: START')
            results.append({'run_tests': run_tests()})
            log.warn('TESTS RUN: PASS')
    finally:
        # make sure we return things back to how they started
        if args.stash_first:
            run('git stash pop -q')

    if all(results):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
    sys.exit(0)

sys.exit(1)
