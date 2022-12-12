#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "run=$(mktemp -d)" 0 "Create run workdir"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun -s "tmt run --id $run --verbose" 2
        rlAssertGrep "project: tmt" $rlRun_LOG
        rlAssertGrep "launch: smoke" $rlRun_LOG
        rlAssertGrep "report: Successfully uploaded." $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -rf $run" 0 "Remove run workdir"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
