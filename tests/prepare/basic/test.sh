#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt run -dddvvvr | tee output"
        rlAssertGrep "Test Management Tool" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -f output"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
