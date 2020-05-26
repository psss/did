#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    for verbosity in '' '-dv' '-ddvv' '-dddvvv'; do
        rlPhaseStartTest "Run $verbosity"
            rlRun "tmt run $verbosity --force --id $run" 2 "Run all plans"
        rlPhaseEnd
    done

    for method in tmt detach; do
        rlPhaseStartTest "Check shell.$method results"
            results="$run/plan/shell/$method/execute/results.yaml"
            rlRun "grep -A1 good:  $results | grep pass" 0 "Check pass"
            rlRun "grep -A1 weird: $results | grep error" 0 "Check error"
            rlRun "grep -A1 bad:   $results | grep fail" 0 "Check fail"
        rlPhaseEnd

        rlPhaseStartTest "Check beakerlib.$method results"
            results="$run/plan/beakerlib/$method/execute/results.yaml"
            rlRun "grep -A1 good:  $results | grep pass" 0 "Check pass"
            rlRun "grep -A1 need:  $results | grep warn" 0 "Check warn"
            rlRun "grep -A1 weird: $results | grep error" 0 "Check error"
            rlRun "grep -A1 bad:   $results | grep fail" 0 "Check fail"
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
