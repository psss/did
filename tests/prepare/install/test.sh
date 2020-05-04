#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Escape package names"
        rlRun "tmt run -adddvvv plan --name escape"
    rlPhaseEnd

    rlPhaseStartTest "Install from epel7 copr"
        rlRun "tmt run -adddvvv plan --name epel7"
    rlPhaseEnd

    rlPhaseStartTest "Install from epel6 copr"
        rlRun "tmt run -adddvvv plan --name epel6"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
