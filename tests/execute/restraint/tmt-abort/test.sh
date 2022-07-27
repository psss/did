#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun -s "tmt run -vvv --remove" 2 "Expect error from execution to tmt-abort."
        # 2 tests discovered but only one is executed due to abort
        rlAssertGrep "1 test executed" $rlRun_LOG
        rlAssertNotGrep "This test should not be executed." $rlRun_LOG
        rlAssertNotGrep "This should not be executed either." $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
