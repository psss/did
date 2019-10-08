# coding: utf-8

""" Default Templates """


TEST_METADATA = """
summary: Concise summary describing what the test does
contact: Name Surname <email@example.com>
test: ./test.sh
""".lstrip()


TEST_SHELL = """
#!/bin/sh -eux

tmp=$(mktemp)
tmt --help > $tmp
grep -C3 'Test Metadata Tool' $tmp
rm $tmp
""".lstrip()


TEST_BEAKERLIB = """
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
        rlAssertGrep "Test Metadata Tool" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TMP" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
""".lstrip()
