#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
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
