#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd invalid-data"
    rlPhaseEnd

    rlPhaseStartTest "Show Invalid Plans"
        rlRun -s "tmt plan show" 2
        rlAssertNotGrep "Traceback" $rlRun_LOG
        rlAssertGrep "Failed to import remote plan" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
