#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Just enable copr"
        rlRun "tmt run -adddvvvr plan --name copr"
    rlPhaseEnd

    rlPhaseStartTest "Escape package names"
        rlRun "tmt run -adddvvvr plan --name escape"
    rlPhaseEnd

    rlPhaseStartTest "Exclude selected packages"
        rlRun "tmt run -adddvvvr plan --name exclude"
    rlPhaseEnd

    rlPhaseStartTest "Install from epel7 copr"
        rlRun "tmt run -adddvvvr plan --name epel7"
    rlPhaseEnd

    rlPhaseStartTest "Install debuginfo packages"
        rlRun "tmt run -adddvvvr plan --name debuginfo"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
