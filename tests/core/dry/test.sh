#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlRun "tmt run --dry"
        rlRun "tmt run --dry -dv"
        rlRun "tmt run --dry -ddvv"
        rlRun "tmt run --dry -dddvvv"
    rlPhaseEnd
rlJournalEnd
