#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "set -o pipefail"
        rlRun "pushd efi"
    rlPhaseEnd

    for interactive in "" "--interactive"; do
        rlPhaseStartTest "Simple reboot test on UEFI booted machine (interactivity: $interactive)"
            rlRun -s "tmt run --scratch -i $run -dddvvva execute -h tmt $interactive"
            rlAssertGrep "Reboot during test '/test' with reboot count 1" $rlRun_LOG
            rlAssertGrep "After first reboot" $rlRun_LOG
            rlAssertGrep "Reboot during test '/test' with reboot count 2" $rlRun_LOG
            rlAssertGrep "After second reboot" $rlRun_LOG
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "rm -rf $run" 0 "Remove run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
