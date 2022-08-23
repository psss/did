#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd $tmp"

        rlRun -s "tmt init"
        rlAssertExists ".fmf/version"
        rlRun "mkdir $tmp/foo && cd $tmp/foo"
    rlPhaseEnd

    rlPhaseStartTest "Test option --dry"
        rlRun -s "tmt init --dry --force"
        rlAssertNotExists "$tmp/foo/.fmf/version"
        rlAssertGrep "Path '$tmp/foo' already has a parent tree root '$tmp'" "$rlRun_LOG"
        rlAssertGrep "Tree '$tmp/foo' would be initialized." "$rlRun_LOG"

        rlRun -s "tmt init --dry <<< no"
        rlAssertNotExists "$tmp/foo/.fmf/version"
        rlAssertGrep "Path '$tmp/foo' already has a parent tree root '$tmp'" "$rlRun_LOG"
        rlAssertGrep "Do you really want to initialize a nested tree?" "$rlRun_LOG"
        rlAssertNotGrep "Tree '$tmp/foo' would be initialized." "$rlRun_LOG"

        rlRun -s "tmt init --dry <<< yes"
        rlAssertNotExists "$tmp/foo/.fmf/version"
        rlAssertGrep "Path '$tmp/foo' already has a parent tree root '$tmp'" "$rlRun_LOG"
        rlAssertGrep "Do you really want to initialize a nested tree?" "$rlRun_LOG"
        rlAssertGrep "Tree '$tmp/foo' would be initialized." "$rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Test option --force"
        rlRun -s "tmt init --force"
        rlAssertExists "$tmp/foo/.fmf/version"
        rlAssertGrep "Path '$tmp/foo' already has a parent tree root '$tmp'" "$rlRun_LOG"
        rlAssertGrep "Tree '$tmp/foo' initialized." "$rlRun_LOG"
        rlRun "rm -rf $tmp/foo/.fmf"
    rlPhaseEnd

    rlPhaseStartTest "Test nested directly"
        rlRun -s "tmt init -t mini <<< no"
        rlAssertGrep "Do you really want to initialize a nested tree?" "$rlRun_LOG"
        rlAssertNotExists "$tmp/foo/.fmf/version"

        rlRun -s "tmt init -t mini <<< yes"
        rlAssertExists "$tmp/foo/.fmf/version"
        rlAssertGrep "Do you really want to initialize a nested tree?" "$rlRun_LOG"
        rlAssertGrep "Applying template 'mini'" "$rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
