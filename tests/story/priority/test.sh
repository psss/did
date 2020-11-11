#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Must Have"
        rlRun -s "tmt story show essential"
        rlAssertGrep "essential story" $rlRun_LOG
        rlAssertGrep "priority must have" $rlRun_LOG
        rlAssertNotGrep "priority should have" $rlRun_LOG
        rlAssertNotGrep "priority could have" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Unknown Priority"
        rlRun -s "tmt story show unknown"
        rlAssertGrep "not prioritized" $rlRun_LOG
        rlAssertNotGrep "priority" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Filter Stories"
        filter="priority:should have | priority:could have"
        rlRun -s "tmt story ls --filter '$filter'"
        rlAssertGrep "/story/important" $rlRun_LOG
        rlAssertGrep "/story/useful" $rlRun_LOG
        rlAssertNotGrep "/story/essential" $rlRun_LOG
        rlAssertNotGrep "/story/unknown" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
