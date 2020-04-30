#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlRun "false" 0 "That's bad!"
    rlPhaseEnd
rlJournalEnd
