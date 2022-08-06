#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlPass "Passing assert"
        sleep 120 # Way more than timeout of 5 seconds imposed by `duration`
    rlPhaseEnd
rlJournalEnd
