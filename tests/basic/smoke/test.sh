#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlRun "did --test --github-approximate-commented last quarter"
    rlPhaseEnd
rlJournalEnd
