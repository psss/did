#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Show a minimal test"
        rlRun -s "tmt tests show mini"
        rlAssertNotGrep "summary" $rlRun_LOG
        rlAssertNotGrep "description" $rlRun_LOG
        rlAssertNotGrep "contact" $rlRun_LOG
        rlAssertNotGrep "component" $rlRun_LOG
        rlAssertNotGrep "id" $rlRun_LOG
        rlAssertGrep "test ./test.sh" $rlRun_LOG
        rlAssertGrep "path /tests" $rlRun_LOG
        rlAssertGrep "framework shell" $rlRun_LOG
        rlAssertGrep "manual false" $rlRun_LOG
        rlAssertNotGrep "require" $rlRun_LOG
        rlAssertNotGrep "recommend" $rlRun_LOG
        rlAssertNotGrep "environment" $rlRun_LOG
        rlAssertGrep "duration 5m" $rlRun_LOG
        rlAssertGrep "enabled true" $rlRun_LOG
        rlAssertNotGrep "order" $rlRun_LOG
        rlAssertGrep "result respect" $rlRun_LOG
        rlAssertNotGrep "tag" $rlRun_LOG
        rlAssertNotGrep "tier" $rlRun_LOG
        rlAssertNotGrep "relates" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Show a full test"
        rlRun -s "tmt tests show full"
        rlAssertGrep "summary Check the test keys are correctly displayed" $rlRun_LOG
        rlAssertGrep "description Some description" $rlRun_LOG
        rlAssertGrep "contact Some Body <somebody@somewhere.org>" $rlRun_LOG
        rlAssertGrep "component package" $rlRun_LOG
        rlAssertGrep "id e3a9a8ed-4585-4e86-80e8-1d99eb5345a9" $rlRun_LOG
        rlAssertGrep "test ./test.sh" $rlRun_LOG
        rlAssertGrep "path /some/path" $rlRun_LOG
        rlAssertGrep "framework beakerlib" $rlRun_LOG
        rlAssertGrep "manual false" $rlRun_LOG
        rlAssertGrep "require.*required-package" $rlRun_LOG
        rlAssertGrep "require.*beakerlib" $rlRun_LOG
        rlAssertGrep "recommend recommended-package" $rlRun_LOG
        rlAssertGrep "environment KEY: VAL" $rlRun_LOG
        rlAssertGrep "duration 3m" $rlRun_LOG
        rlAssertGrep "enabled true" $rlRun_LOG
        rlAssertGrep "order 70" $rlRun_LOG
        rlAssertGrep "result respect" $rlRun_LOG
        rlAssertGrep "tag foo" $rlRun_LOG
        rlAssertGrep "tier 3" $rlRun_LOG
        rlAssertGrep "relates https://something.org/related" $rlRun_LOG
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
