#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Import Plan Show"
        rlRun -s "tmt plan"
	rlAssertNotGrep "warn" $rlRun_LOG
        rlAssertGrep "Found 2 plans" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Import Plan Show detailed"
        rlRun -s "tmt plan show -v"
        rlAssertNotGrep "warn" $rlRun_LOG
        rlAssertGrep "imported plan" $rlRun_LOG
        rlAssertGrep "/plans/minimal-import" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Import Plan Run Discover"
        rlRun -s "tmt run discover"
        rlAssertGrep "/plans/minimal-import" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Import Plan Run"
        rlRun -s "tmt run -a"
        rlAssertGrep "/plans/minimal-import" $rlRun_LOG
        rlAssertGrep "summary: 1 test passed" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
