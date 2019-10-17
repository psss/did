# coding: utf-8

""" Default Templates """

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Test Templates
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TEST = dict()

TEST_METADATA = """
summary: Concise summary describing what the test does
contact: Name Surname <email@example.com>
test: ./test.sh
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

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="tmt"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TMP=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TMP"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt --help | tee output" 0 "Check help message"
        rlAssertGrep "Test Management Tool" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TMP" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
""".lstrip()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Plan Templates
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PLAN = dict()

PLAN['mini'] = """
summary:
    Just a basic smoke test
execute:
    script: tmt --help
""".lstrip()

PLAN['full'] = """
summary:
    Essential command line features
discover:
    how: fmf
    repository: https://github.com/psss/tmt
prepare:
    how: ansible
    playbooks: plans/packages.yml
execute:
    how: beakerlib
""".lstrip()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Story Templates
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

STORY = dict()

STORY['mini'] = """
story: As a user I want to do this and that.
examples: One example is worth thousand words.
""".lstrip()

STORY['full'] = """
summary:
    Short description summarizing the story.
story:
    As a user I want to do this and that
    so that I can achieve this.
description:
    Text describing all important aspects of the object.
    Usually spans across several paragraphs. It should not
    contain detailed examples. Those should be stored
    under the 'examples' attribute.
examples:
    - One example is worth thousand words.
    - Of course, there can be more than one.
""".lstrip()
