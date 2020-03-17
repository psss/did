#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="tmt"

rlJournalStart
    rlPhaseStartTest
        rlRun "echo $TESTING | grep WORKS"
    rlPhaseEnd
rlJournalEnd
