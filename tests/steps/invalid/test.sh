#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt run --scratch -i $tmp 2>&1 | tee output" 2 "Expect the run to fail"
        rlAssertGrep "Unsupported provision method" "output"
        rlRun "tmt run --scratch -i $tmp discover 2>&1 | tee output" 0 \
            "Invalid step not enabled, do not fail"
        rlAssertGrep "warn: Unsupported provision method" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm output"
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
