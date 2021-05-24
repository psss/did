#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1


rlJournalStart
    rlPhaseStartTest
        case $1 in
            pass)
                rlPass "pass"
                ;;
            fail)
                rlFail "fail"
                ;;
            timeout)
                sleep 10
                ;;
        esac
    rlPhaseEnd
rlJournalEnd
