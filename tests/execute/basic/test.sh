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

    # NOTE: regular expressions below are slightly less trivial. The order of keys in results.yaml
    # is not fixed, if parser decides, they may swap positions, therefore expressions try to match
    # a *multiline section* of results.yaml that should include test and whatever we're grepping
    # for. Non-greedy matching is used to limit to just a single result in results.yaml, otherwise
    # grep might not reveal a `result` key missing in a particular results because it'd exist in
    # the *next* result in the file.
    for method in tmt; do
        rlPhaseStartTest "Check shell.$method results"
            results="$run/plan/shell/$method/execute/results.yaml"

            rlRun "grep -Pzo '(?sm)^/test/shell/good:$.*?^ *result: pass$' $results" 0 "Check pass"
            check_duration "$results" "good:"

            rlRun "grep -Pzo '(?sm)^/test/shell/weird:$.*?^ *result: error$' $results" 0 "Check error"
            check_duration "$results" "weird:"

            rlRun "grep -Pzo '(?sm)^/test/shell/bad:$.*?^ *result: fail$' $results" 0 "Check fail"
            check_duration "$results" "bad:"

            # Check log file exists
            rlRun "grep -Pzo '(?sm)^/test/shell/good:$.*?^ +log:$.*?^ +- data/.+?$' $results | grep output.txt" \
              0 "Check output.txt log exists in $results"
        rlPhaseEnd

        rlPhaseStartTest "Check beakerlib.$method results"
            results="$run/plan/beakerlib/$method/execute/results.yaml"

            rlRun "grep -Pzo '(?sm)^/test/beakerlib/good:$.*?^ *result: pass$' $results" 0 "Check pass"
            check_duration "$results" "good:"

            rlRun "grep -Pzo '(?sm)^/test/beakerlib/need:$.*?^ *result: warn$' $results" 0 "Check warn"
            check_duration "$results" "need:"

            rlRun "grep -Pzo '(?sm)^/test/beakerlib/weird:$.*?^ *result: error$' $results" 0 "Check error"
            check_duration "$results" "weird:"

            rlRun "grep -Pzo '(?sm)^/test/beakerlib/bad:$.*?^ *result: fail$' $results" 0 "Check fail"
            check_duration "$results" "bad:"

            # Check log files exist
            rlRun "grep -Pzo '(?sm)^/test/beakerlib/good:$.*^ +log:$.*?^ +- data/.+?$' $results | grep output.txt" \
              0 "Check output.txt log exists"
            rlRun "grep -Pzo '(?sm)^/test/beakerlib/good:$.*^ +log:$.*?^ +- data/.+?$' $results | grep journal.txt" \
              0 "Check journal.txt log exists"
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
