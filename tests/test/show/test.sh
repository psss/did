#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "List all tests by default"
        rlRun -s "tmt tests ls"
        rlAssertGrep "/tests/enabled" $rlRun_LOG
        rlAssertGrep "/tests/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "List only enabled tests"
        rlRun -s "tmt tests ls --enabled"
        rlAssertGrep "/tests/enabled" $rlRun_LOG
        rlAssertNotGrep "/tests/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "List only disabled tests"
        rlRun -s "tmt tests ls --disabled"
        rlAssertNotGrep "/tests/enabled" $rlRun_LOG
        rlAssertGrep "/tests/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show all tests by default"
        rlRun -s "tmt tests show"
        rlAssertGrep "/tests/enabled" $rlRun_LOG
        rlAssertGrep "/tests/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show only enabled tests"
        rlRun -s "tmt tests show --enabled"
        rlAssertGrep "/tests/enabled" $rlRun_LOG
        rlAssertGrep "enabled true" $rlRun_LOG
        rlAssertNotGrep "/tests/disabled" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show only disabled tests"
        rlRun -s "tmt tests show --disabled"
        rlAssertNotGrep "/tests/enabled" $rlRun_LOG
        rlAssertGrep "/tests/disabled" $rlRun_LOG
        rlAssertGrep "enabled false" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show enabled tests with filter including '&'"
        rlRun -s "tmt tests ls --filter 'enabled:true&test:echo' --enabled"
        rlAssertNotGrep "/tests/enabled01" $rlRun_LOG
        rlAssertGrep    "/tests/enabled02" $rlRun_LOG
        rlAssertNotGrep "/tests/disabled01" $rlRun_LOG
        rlAssertNotGrep "/tests/disabled02" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show enabled tests with filter including '|'"
        rlRun -s "tmt tests ls --filter 'enabled:true|test:echo' --enabled"
        rlAssertGrep    "/tests/enabled01" $rlRun_LOG
        rlAssertGrep    "/tests/enabled02" $rlRun_LOG
        rlAssertNotGrep "/tests/disabled01" $rlRun_LOG
        rlAssertNotGrep "/tests/disabled02" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show disabled tests with filter including '&'"
        rlRun -s "tmt tests ls --filter 'enabled:true&test:echo' --disabled"
        rlAssertNotGrep "/tests/enabled01" $rlRun_LOG
        rlAssertNotGrep "/tests/enabled02" $rlRun_LOG
        rlAssertNotGrep "/tests/disabled01" $rlRun_LOG
        rlAssertNotGrep "/tests/disabled02" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show disabled tests with filter including '|'"
        rlRun -s "tmt tests ls --filter 'enabled:true|test:echo' --disabled"
        rlAssertNotGrep "/tests/enabled01" $rlRun_LOG
        rlAssertNotGrep "/tests/enabled02" $rlRun_LOG
        rlAssertNotGrep "/tests/disabled01" $rlRun_LOG
        rlAssertGrep    "/tests/disabled02" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
