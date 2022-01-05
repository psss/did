#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Check reboot variables"
        for variable in TMT_REBOOT_COUNT RSTRNT_REBOOTCOUNT REBOOTCOUNT; do
            rlLog "$variable=${!variable}"
            rlRun "[[ -n '${!variable}' ]]" 0 \
                "Reboot count variable '$variable' must be defined."
        done
    rlPhaseEnd

    # Before
    if [ "$TMT_REBOOT_COUNT" == "0" ]; then
        rlPhaseStartTest "Before reboot"
            rlRun "tmt-reboot" 0 "Reboot using 'tmt-reboot'."
        rlPhaseEnd

    # First
    elif [ "$TMT_REBOOT_COUNT" == "1" ]; then
        rlPhaseStartTest "After first reboot"
            rlRun "rstrnt-reboot" 0 "Reboot using 'rstrnt-reboot'."
        rlPhaseEnd

    # Second
    elif [ "$TMT_REBOOT_COUNT" == "2" ]; then
        rlPhaseStartTest "After second reboot"
            rlRun "rhts-reboot" 0 "Reboot using 'rhts-reboot'."
        rlPhaseEnd

    # Third
    elif [ "$TMT_REBOOT_COUNT" == "3" ]; then
        rlPhaseStartTest "After third reboot"
            rlLog "We're done!"
        rlPhaseEnd

    # Weird
    else
        rlPhaseStartTest "Weird"
            rlFail "Unexpected reboot count '$TMT_REBOOT_COUNT'."
        rlPhaseEnd
    fi
rlJournalEnd
