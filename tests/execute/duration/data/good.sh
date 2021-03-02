#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlPass "Passing assert"
    rlPhaseEnd
rlJournalEnd
