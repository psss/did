#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Reboot using rhts-reboot"
        if [ -z "$REBOOT_COUNT" ] || [ $REBOOT_COUNT -eq 0 ]; then
            rlRun "rhts-reboot" 0 "Reboot the machine"
        elif [ "$REBOOT_COUNT" -eq 1 ]; then
            rlRun "echo 'After first reboot'"
        fi
    rlPhaseEnd

    rlPhaseStartTest "Reboot using rstrnt-reboot"
        if [ $REBOOT_COUNT -eq 1 ]; then
            rlRun "rstrnt-reboot" 0 "Reboot the machine"
        elif [ "$REBOOT_COUNT" -eq 2 ]; then
            rlRun "echo 'After second reboot'"
        fi
    rlPhaseEnd

    rlPhaseStartTest "Reboot using tmt-reboot"
        if [ $REBOOT_COUNT -eq 2 ]; then
            rlRun "tmt-reboot" 0 "Reboot the machine"
        elif [ "$REBOOT_COUNT" -eq 3 ]; then
            rlRun "echo 'After third reboot'"
        fi
    rlPhaseEnd
rlJournalEnd
