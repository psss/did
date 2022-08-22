#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Show a minimal story"
        rlRun -s "tmt stories show mini"
        rlAssertNotGrep "summary" $rlRun_LOG
        rlAssertNotGrep "title" $rlRun_LOG
        rlAssertGrep "story As a user I want this and that" $rlRun_LOG
        rlAssertNotGrep "description" $rlRun_LOG
        rlAssertNotGrep "priority" $rlRun_LOG
        rlAssertNotGrep "example" $rlRun_LOG
        rlAssertNotGrep "id" $rlRun_LOG
        rlAssertGrep "enabled true" $rlRun_LOG
        rlAssertNotGrep "order" $rlRun_LOG
        rlAssertNotGrep "tag" $rlRun_LOG
        rlAssertNotGrep "tier" $rlRun_LOG
        rlAssertNotGrep "relates" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show a full story"
        rlRun -s "tmt stories show full"
        rlAssertGrep "summary Story keys are correctly displayed" $rlRun_LOG
        rlAssertGrep "title Concise title" $rlRun_LOG
        rlAssertGrep "story As a user I want this and that" $rlRun_LOG
        rlAssertGrep "description Some description" $rlRun_LOG
        rlAssertGrep "priority must have" $rlRun_LOG
        rlAssertGrep "example Inspiring example" $rlRun_LOG
        rlAssertGrep "id e3a9a8ed-4585-4e86-80e8-1d99eb5345a9" $rlRun_LOG
        rlAssertGrep "enabled true" $rlRun_LOG
        rlAssertGrep "order 70" $rlRun_LOG
        rlAssertGrep "tag foo" $rlRun_LOG
        rlAssertGrep "tier 3" $rlRun_LOG
        rlAssertGrep "relates https://something.org/related" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "List all stories by default"
        rlRun -s "tmt stories ls"
        rlAssertGrep "/stories/enabled" $rlRun_LOG
        rlAssertGrep "/stories/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "List only enabled stories"
        rlRun -s "tmt stories ls --enabled"
        rlAssertGrep "/stories/enabled" $rlRun_LOG
        rlAssertNotGrep "/stories/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "List only disabled stories"
        rlRun -s "tmt stories ls --disabled"
        rlAssertNotGrep "/stories/enabled" $rlRun_LOG
        rlAssertGrep "/stories/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show all stories by default"
        rlRun -s "tmt stories show"
        rlAssertGrep "/stories/enabled" $rlRun_LOG
        rlAssertGrep "/stories/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show only enabled stories"
        rlRun -s "tmt stories show --enabled"
        rlAssertGrep "/stories/enabled" $rlRun_LOG
        rlAssertGrep "enabled true" $rlRun_LOG
        rlAssertNotGrep "/stories/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show only disabled stories"
        rlRun -s "tmt stories show --disabled"
        rlAssertNotGrep "/stories/enabled" $rlRun_LOG
        rlAssertGrep "/stories/disabled" $rlRun_LOG
        rlAssertGrep "enabled false" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
