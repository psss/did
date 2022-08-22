#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
        rlRun "output=\$(mktemp)"
    rlPhaseEnd

    rlPhaseStartTest "Show a minimal plan"
        rlRun -s "tmt plans show mini"
        rlAssertGrep "how tmt" $rlRun_LOG
        rlAssertGrep "script /bin/true" $rlRun_LOG
        rlAssertGrep "enabled true" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show a full plan"
        rlRun -s "tmt plans show full"
        # Core
        rlAssertGrep "summary Plan keys are correctly displayed" $rlRun_LOG
        rlAssertGrep "description Some description" $rlRun_LOG
        rlAssertGrep "id e3a9a8ed-4585-4e86-80e8-1d99eb5345a9" $rlRun_LOG
        rlAssertGrep "enabled true" $rlRun_LOG
        rlAssertGrep "order 70" $rlRun_LOG
        rlAssertGrep "tag foo" $rlRun_LOG
        rlAssertGrep "tier 3" $rlRun_LOG
        rlAssertGrep "relates https://something.org/related" $rlRun_LOG

        # Steps
        rlRun "grep -A2 '^ *discover' $rlRun_LOG > $output"
        rlAssertGrep "    how fmf" $output
        rlAssertGrep "    filter tier:1" $output
        rlRun "grep -A2 '^ *provision' $rlRun_LOG > $output"
        rlAssertGrep "    how container" $output
        rlAssertGrep "    image fedora" $output
        rlRun "grep -A2 '^ *prepare' $rlRun_LOG > $output"
        rlAssertGrep "    how shell" $output
        rlAssertGrep "    script systemctl start libvirtd" $output
        rlRun "grep -A2 '^ *report' $rlRun_LOG > $output"
        rlAssertGrep "    how html" $output
        rlAssertGrep "    open true" $output
        rlRun "grep -A2 '^ *finish' $rlRun_LOG > $output"
        rlAssertGrep "    how ansible" $output
        rlAssertGrep "    playbook cleanup.yaml" $output

        # Extra
        rlAssertGrep "environment KEY: VAL" $rlRun_LOG
        rlAssertGrep "context distro: fedora" $rlRun_LOG
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
        rlRun "rm $output"
    rlPhaseEnd
rlJournalEnd
