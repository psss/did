#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1
BOOTCURRENT_OUTPUTFILE="$TMT_TEST_DATA/bootcurrent"

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
            if [ $(command -v efibootmgr) &>/dev/null ]; then
                rlLog "efibootmgr installed."
                rlRun "echo $(efibootmgr | awk '/BootCurrent/ { print $2 }') > $BOOTCURRENT_OUTPUTFILE" 0 "Write BootCurrent value to a file."
                rlRun "current=$(cat $BOOTCURRENT_OUTPUTFILE)"
                rlLog "BootCurrent=$current"
            fi
            rlRun "tmt-reboot" 0 "Reboot using 'tmt-reboot'."
            # Add sleep to check that the test is killed by tmt-reboot
            rlRun "sleep 3600"
        rlPhaseEnd

    # First
    elif [ "$TMT_REBOOT_COUNT" == "1" ]; then
        rlPhaseStartTest "After first reboot"
            rlRun "current=$(cat $BOOTCURRENT_OUTPUTFILE)"
            rlRun "count=$(grep \"efibootmgr -n $current\" /var/log/messages | wc -l)"
            rlAssertEqual "Ensure BootNext set to BootCurrent value." $count 1
            rlRun "tmt-reboot -e" 0 "Reboot using 'tmt-reboot -e'."
        rlPhaseEnd

    # Second
    elif [ "$TMT_REBOOT_COUNT" == "2" ]; then
        rlPhaseStartTest "After second reboot"
            rlRun "current=$(cat $BOOTCURRENT_OUTPUTFILE)"
            rlRun "count=$(grep \"efibootmgr -n $current\" /var/log/messages | wc -l)"
            rlAssertEqual "Ensure BootNext set to BootCurrent value." $count 1
        rlPhaseEnd

    # Weird
    else
        rlPhaseStartTest "Weird"
            rlFail "Unexpected reboot count '$TMT_REBOOT_COUNT'."
        rlPhaseEnd
    fi

    rlPhaseStartCleanup
        rlRun "rm -f $BOOTCURRENT_OUTPUTFILE"
    rlPhaseEnd
rlJournalEnd
