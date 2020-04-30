#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Run"
        rlRun "tmt run -i $run" 0 "Check help message"
    rlPhaseEnd

    rlPhaseStartTest "Shell"
        results="$run/plan/shell/execute/results.yaml"
        rlRun "grep -A1 good:  $results | grep pass" 0 "Check pass"
        rlRun "grep -A1 weird: $results | grep error" 0 "Check error"
        rlRun "grep -A1 bad:   $results | grep fail" 0 "Check fail"
    rlPhaseEnd

    rlPhaseStartTest "BeakerLib"
        results="$run/plan/beakerlib/execute/results.yaml"
        rlRun "grep -A1 good:  $results | grep pass" 0 "Check pass"
        rlRun "grep -A1 need:  $results | grep warn" 0 "Check warn"
        rlRun "grep -A1 weird: $results | grep error" 0 "Check error"
        rlRun "grep -A1 bad:   $results | grep fail" 0 "Check fail"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
