#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "List all plans by default"
        rlRun -s "tmt plans ls"
        rlAssertGrep "/plans/enabled" $rlRun_LOG
        rlAssertGrep "/plans/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "List only enabled plans"
        rlRun -s "tmt plans ls --enabled"
        rlAssertGrep "/plans/enabled" $rlRun_LOG
        rlAssertNotGrep "/plans/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "List only disabled plans"
        rlRun -s "tmt plans ls --disabled"
        rlAssertNotGrep "/plans/enabled" $rlRun_LOG
        rlAssertGrep "/plans/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show all plans by default"
        rlRun -s "tmt plans show"
        rlAssertGrep "/plans/enabled" $rlRun_LOG
        rlAssertGrep "/plans/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show only enabled plans"
        rlRun -s "tmt plans show --enabled"
        rlAssertGrep "/plans/enabled" $rlRun_LOG
        rlAssertGrep "enabled true" $rlRun_LOG
        rlAssertNotGrep "/plans/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show only disabled plans"
        rlRun -s "tmt plans show --disabled"
        rlAssertNotGrep "/plans/enabled" $rlRun_LOG
        rlAssertGrep "/plans/disabled" $rlRun_LOG
        rlAssertGrep "enabled false" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
