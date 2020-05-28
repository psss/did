#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlRun "pushd data"
        rlRun "tmt run"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
