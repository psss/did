#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Correct story"
        rlRun -s "tmt stories lint good" 1
        rlAssertGrep "pass correct attributes are used" $rlRun_LOG
        rlAssertNotGrep "warn summary" $rlRun_LOG
        rlAssertNotGrep "fail" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Incorrect story"
        rlRun -s "tmt stories lint long_summary" 1
        rlAssertGrep "warn summary should not exceed 50 characters" $rlRun_LOG
        rlRun "rm $rlRun_LOG"

        rlRun -s "tmt stories lint typo_in_key" 1
        rlAssertGrep "fail unknown attribute '.*' is used" $rlRun_LOG
        rlAssertNotGrep "pass correct attributes are used" $rlRun_LOG
        rlRun "rm $rlRun_LOG"

        rlRun -s "tmt stories lint missing_story" 1
        rlAssertGrep "fail story is required" $rlRun_LOG
        rlAssertGrep "pass correct attributes are used" $rlRun_LOG
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
