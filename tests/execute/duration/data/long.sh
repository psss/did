#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlPass "Passing assert"
        sleep 10 # more than timeout
    rlPhaseEnd
rlJournalEnd
