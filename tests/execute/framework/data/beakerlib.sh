#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlRun "echo 'I am a beakerlib test.'"
    rlPhaseEnd
rlJournalEnd
