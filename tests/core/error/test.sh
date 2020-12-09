#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd $tmp"
    rlPhaseEnd

    rlPhaseStartTest "Test error output"
        rlRun "tmt plan ls 2>output" 2 "tmt plan ls without metadata"
        rlRun "cat output"
        rlAssertGrep "No metadata found" output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
