#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun -s "tmt run -vvv --id \${run}" 2 "Expect error from execution to tmt-abort."
        # 2 tests discovered but only one is executed due to abort
        rlAssertGrep "1 test executed" $rlRun_LOG
        rlAssertNotGrep "This test should not be executed." $rlRun_LOG
        rlAssertNotGrep "This should not be executed either." $rlRun_LOG

        rlAssertGrep "result: error" "${run}/plan/execute/results.yaml"
        rlAssertGrep "note: aborted" "${run}/plan/execute/results.yaml"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r ${run}" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
