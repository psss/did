#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    function check_correct_order() {
        local -n f_order=$1
        local output=$2
        for ((i = 0; i < ${#f_order[@]}; i++)); do
          rlRun "sed ''"$((i+1))"','"$((i+1))"'!d' $output \
            | grep \"${f_order[i]}\""
        done
    }

    rlPhaseStartSetup
        rlRun "output=\$(mktemp)" 0 "Create output file"
        rlRun "set -o pipefail"
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Order with tmt ls"
        for tmt in 'plans' 'stories'; do
          order=(negative_1 zero third fourth no_order none)
          rlRun "tmt $tmt ls | tee $output"
          check_correct_order order "$output"
        done

        order=(negative_2 negative_1 zero one two three fourth no_order none)
        rlRun "tmt tests ls | tee $output"
        check_correct_order order "$output"
    rlPhaseEnd

    rlPhaseStartTest "Order with tmt show"
        for tmt in 'plans' 'stories'; do
          for ((i = 0; i < 4; i++)); do
            order=(negative_1 zero third fourth)
            order_value=(-1 0 3 4)
            rlRun "tmt $tmt show \"${order[i]}\" | grep order | tee $output"
            rlAssertGrep "${order_value[i]}" $output
          done
          for ((i = 0; i < 2; i++)); do
            order=(no_order none)
            order_value=(50 50)
            rlRun "tmt $tmt show \"${order[i]}\" | grep order | tee $output"
            rlAssertNotGrep "${order_value[i]}" $output
          done
        done
        for ((i = 0; i < 7; i++)); do
          order=(negative_2 negative_1 zero one two three fourth)
          order_value=(-2 -1 0 1 2 3 4)
          rlRun "tmt tests show \"${order[i]}\" | grep order | tee $output"
          rlAssertGrep "${order_value[i]}" $output
        done
        for ((i = 0; i < 2; i++)); do
          order=(no_order none)
          order_value=(50 50)
          rlRun "tmt tests show \"${order[i]}\" | grep order | tee $output"
          rlAssertNotGrep "${order_value[i]}" $output
        done
    rlPhaseEnd

    discover="tmt run -r finish -q discover"

    rlPhaseStartTest "Tests order with tmt run discover plan"
        order=(negative_2 one two three fourth negative_2 one two three)
        rlRun "$discover -v plan -n third 2>&1 >/dev/null | grep ' /tests/' | tee $output"
        check_correct_order order "$output"
    rlPhaseEnd

    rlPhaseStartTest "Tests order with tmt run discover plan and test"
        order=(negative_2 one two three negative_2 one two three)
        rlRun "$discover -v plan -n third test -n third 2>&1 >/dev/null | grep ' /tests/' | tee $output"
        check_correct_order order "$output"
        order=(fourth)
        rlRun "$discover -v plan -n third test -n fourth 2>&1 >/dev/null | grep ' /tests/' | tee $output"
        check_correct_order order "$output"
    rlPhaseEnd

    rlPhaseStartTest "Plans order with tmt run discover"
        order=(negative_1 zero third fourth no_order none)
        rlRun "tmt run -r finish discover -q 2>&1 >/dev/null | grep -v 'warn:' | grep plan | tee $output"
        check_correct_order order "$output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm $output" 0 "Remove output file"
    rlPhaseEnd
rlJournalEnd
