#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun -s "tmt plan export ." 0 "Export plan"
        rlAssertGrep "- name: /plan/plan_no_L2_key" $rlRun_LOG
        rlAssertGrep "- name: /plan/plan_L2_context" $rlRun_LOG
        rlAssertGrep "- name: /plan/plan_L2_environment" $rlRun_LOG
        rlAssertGrep "- name: /plan/plan_L2_gate" $rlRun_LOG
        rlAssertGrep "summary: Testing plans to export" $rlRun_LOG
        rlAssertGrep "discover:" $rlRun_LOG
        rlAssertGrep "execute:" $rlRun_LOG
        rm -f $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "tmt plan export /plan/plan_no_L2_key"
        rlRun -s "tmt plan export /plan/plan_no_L2_key" 0 "Export plan"
        rlAssertGrep "- name: /plan/plan_no_L2_key" $rlRun_LOG
        rlAssertGrep "summary: Testing plans to export" $rlRun_LOG
        rlAssertGrep "discover:" $rlRun_LOG
        rlAssertGrep "execute:" $rlRun_LOG
        rm -f $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "tmt plan export /plan/plan_L2_context"
        rlRun -s "tmt plan export /plan/plan_L2_context" 0 "Export plan"
        rlAssertGrep "- name: /plan/plan_L2_context" $rlRun_LOG
        rlAssertGrep "summary: Testing plans to export" $rlRun_LOG
        rlAssertGrep "discover:" $rlRun_LOG
        rlAssertGrep "execute:" $rlRun_LOG
        rlAssertGrep "context:" $rlRun_LOG
        rlAssertGrep "component: dash" $rlRun_LOG
        rm -f $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "tmt plan export /plan/plan_L2_environment"
        rlRun -s "tmt plan export /plan/plan_L2_environment" 0 "Export plan"
        rlAssertGrep "- name: /plan/plan_L2_environment" $rlRun_LOG
        rlAssertGrep "summary: Testing plans to export" $rlRun_LOG
        rlAssertGrep "discover:" $rlRun_LOG
        rlAssertGrep "execute:" $rlRun_LOG
        rlAssertGrep "environment:" $rlRun_LOG
        rlAssertGrep "RELEASE: f35" $rlRun_LOG
        rm -f $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "tmt plan export /plan/plan_L2_gate"
        rlRun -s "tmt plan export /plan/plan_L2_gate" 0 "Export plan"
        rlAssertGrep "- name: /plan/plan_L2_gate" $rlRun_LOG
        rlAssertGrep "summary: Testing plans to export" $rlRun_LOG
        rlAssertGrep "discover:" $rlRun_LOG
        rlAssertGrep "execute:" $rlRun_LOG
        rlAssertGrep "gate:" $rlRun_LOG
        rlAssertGrep "- merge-pull-request" $rlRun_LOG
        rlAssertGrep "- add-build-to-update" $rlRun_LOG
        rlAssertGrep "- add-build-to-compose" $rlRun_LOG
        rm -f $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
