#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "set -o pipefail"
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Simple reboot test"
        rlRun -s "tmt run -i $run -dddvvv"
        rlAssertGrep "Reboot during test '/test' with reboot count 1" $rlRun_LOG
        rlAssertGrep "After first reboot" $rlRun_LOG
        rlAssertGrep "Reboot during test '/test' with reboot count 2" $rlRun_LOG
        rlAssertGrep "After second reboot" $rlRun_LOG
        rlAssertGrep "Reboot during test '/test' with reboot count 3" $rlRun_LOG
        rlAssertGrep "After third reboot" $rlRun_LOG
        rlRun "rm $rlRun_LOG"

        # Check that the whole output log is kept
        rlRun "log=$run/plan/execute/data/test/output.txt"
        rlAssertGrep "After first reboot" $log
        rlAssertGrep "After second reboot" $log
        rlAssertGrep "After third reboot" $log
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -rf output $run" 0 "Remove run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
