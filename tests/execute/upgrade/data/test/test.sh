#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlRun "bash --help" 0 "Check help message"
        rlLog "IN_PLACE_UPGRADE=$IN_PLACE_UPGRADE"
    rlPhaseEnd
rlJournalEnd
