#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

REBOOT_COUNT=${REBOOT_COUNT:-0}

rlJournalStart
    rlPhaseStartSetup
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Reboot using rhts-reboot"
        if [ "$REBOOT_COUNT" -eq 0 ]; then
            rlRun "rhts-reboot" 0 "Reboot the machine"
        elif [ "$REBOOT_COUNT" -eq 1 ]; then
            rlLog "After first reboot"
        fi
    rlPhaseEnd

    rlPhaseStartTest "Reboot using rstrnt-reboot"
        if [ "$REBOOT_COUNT" -eq 1 ]; then
            rlRun "rstrnt-reboot" 0 "Reboot the machine"
        elif [ "$REBOOT_COUNT" -eq 2 ]; then
            rlLog "After second reboot"
        fi
    rlPhaseEnd

    rlPhaseStartTest "Reboot using tmt-reboot"
        if [ "$REBOOT_COUNT" -eq 2 ]; then
            rlRun "tmt-reboot" 0 "Reboot the machine"
        elif [ "$REBOOT_COUNT" -eq 3 ]; then
            rlLog "After third reboot"
        fi
    rlPhaseEnd
rlJournalEnd
