#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlRun "tmt run --dry -r"
        rlRun "tmt run --dry -dvr"
        rlRun "tmt run --dry -ddvvr"
        rlRun "tmt run --dry -dddvvvr"
    rlPhaseEnd
rlJournalEnd
