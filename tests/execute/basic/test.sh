#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    function check_duration() {
        local result_file=$1
        local results=$2
        DURATION_REGEXP="^(((([0-1][0-9])|(2[0-3])):?[0-5][0-9]:?[0-5][0-9]+$))"
        DURATION=$(grep -A5 "$results" "$result_file" | grep "duration:" | awk '{print $2}')
        if [[ "$DURATION" =~ $DURATION_REGEXP ]]; then
          rlRun "true" 0 "duration is in HH:MM:SS format"
        else
          rlRun "false" 0 "duration isn't in HH:MM:SS format"
        fi
    }

    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    for verbosity in '' '-dv' '-ddvv' '-dddvvv'; do
        rlPhaseStartTest "Run $verbosity"
            rlRun "tmt run $verbosity --scratch --id $run" 2 "Run all plans"
        rlPhaseEnd
    done

    for method in tmt detach; do
        rlPhaseStartTest "Check shell.$method results"
            results="$run/plan/shell/$method/execute/results.yaml"
            rlRun "grep -A1 good:  $results | grep pass" 0 "Check pass"
            check_duration "$results" "good:"

            rlRun "grep -A1 weird: $results | grep error" 0 "Check error"
            check_duration "$results" "weird:"

            rlRun "grep -A1 bad:   $results | grep fail" 0 "Check fail"
            check_duration "$results" "bad:"

            # Check log file exists
            rlRun "grep -A3 good:  $results | grep -A1 log: | grep output.txt" \
              0 "Check output.txt log exists in $results"
        rlPhaseEnd

        rlPhaseStartTest "Check beakerlib.$method results"
            results="$run/plan/beakerlib/$method/execute/results.yaml"
            rlRun "grep -A1 good:  $results | grep pass" 0 "Check pass"
            check_duration "$results" "good:"

            rlRun "grep -A1 need:  $results | grep warn" 0 "Check warn"
            check_duration "$results" "need:"

            rlRun "grep -A1 weird: $results | grep error" 0 "Check error"
            check_duration "$results" "weird:"

            rlRun "grep -A1 bad:   $results | grep fail" 0 "Check fail"
            check_duration "$results" "bad:"

            # Check log files exist
            rlRun "grep -A3 good:  $results | grep -A1 log: | grep output.txt" \
              0 "Check output.txt log exists"
            rlRun "grep -A4 good:  $results | grep -A2 log: | grep journal.txt" \
              0 "Check journal.txt log exists"
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
