#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Prepare"
        rlRun "tmt run -i $tmp provision prepare"
        rlRun "ls -l $tmp"
        rlAssertExists "$tmp/cleanup-test"
    rlPhaseEnd

    rlPhaseStartTest "Finish"
        rlRun "tmt run -i $tmp finish"
        rlRun "ls -l $tmp"
        rlAssertNotExists "$tmp/cleanup-test"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
