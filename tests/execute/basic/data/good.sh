#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlRun "true" 0 "That's good!"
    rlPhaseEnd
rlJournalEnd
