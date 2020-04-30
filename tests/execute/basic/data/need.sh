#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartCleanup
        rlRun "false" 0 "Leaving dirty!"
    rlPhaseEnd
rlJournalEnd
