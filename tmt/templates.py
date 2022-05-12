# coding: utf-8

""" Default Templates """

from typing import Dict

INIT_TEMPLATES = ['mini', 'base', 'full']

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Test Templates
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TEST: Dict[str, str] = dict()
TEST_METADATA: Dict[str, str] = dict()

TEST_METADATA['shell'] = """
summary: Concise summary describing what the test does
test: ./test.sh
""".lstrip()

TEST_METADATA['beakerlib'] = """
summary: Concise summary describing what the test does
test: ./test.sh
framework: beakerlib
""".lstrip()

TEST['shell'] = """
#!/bin/sh -eux

tmp=$(mktemp)
tmt --help > $tmp
grep -C3 'Test Management Tool' $tmp
rm $tmp
""".lstrip()

TEST['beakerlib'] = r"""
#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt --help | tee output" 0 "Check help message"
        rlAssertGrep "Test Management Tool" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
""".lstrip()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Plan Templates
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DEFAULT_PLAN = """
/plans/default:
    discover:
        how: fmf
    execute:
        how: tmt
""".lstrip()

PLAN = dict()

PLAN['mini'] = """
summary:
    Basic smoke test
execute:
    script: tmt --help
""".lstrip()

PLAN['base'] = """
summary:
    Basic smoke test
discover:
    how: fmf
execute:
    how: tmt
""".lstrip()

PLAN['full'] = """
summary:
    Essential command line features
discover:
    how: fmf
    url: https://github.com/teemtee/tmt
prepare:
    how: ansible
    playbook: plans/packages.yml
execute:
    how: tmt
""".lstrip()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Story Templates
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

STORY = dict()

STORY['mini'] = """
story: As a user I want to do this and that.
example: One example is worth thousand words.
""".lstrip()

STORY['base'] = """
summary:
    Short description summarizing the story
story:
    As a user I want to do this and that
    so that I can achieve this.
example:
    - One example is worth thousand words.
    - Of course, there can be more than one.
""".lstrip()

STORY['full'] = """
summary:
    Short description summarizing the story
story:
    As a user I want to do this and that
    so that I can achieve this.
description:
    Text describing all important aspects of the object.
    Usually spans across several paragraphs. It should not
    contain detailed examples. Those should be stored
    under the 'examples' attribute.
example:
    - One example is worth thousand words.
    - Of course, there can be more than one.
""".lstrip()
