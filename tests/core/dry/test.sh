#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest "Test debug/verbose levels"
        rlRun "tmt run --dry -r"
        rlRun "tmt run --dry -dvr"
        rlRun "tmt run --dry -ddvvr"
        rlRun "tmt run --dry -dddvvvr"
    rlPhaseEnd

    rlPhaseStartTest "Dry provision propagation"
        rlRun "tmt run --all --remove provision --how virtual --dry"
    rlPhaseEnd
rlJournalEnd
