#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

steps='discover provision prepare execute report finish'

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    for selected_step in $steps; do
        rlPhaseStartTest "Select $selected_step"
            [[ $selected_step == execute ]] && exitcode=1 || exitcode=0
            rlRun "tmt run $selected_step | tee output" $exitcode
            for step in $steps; do
                if [[ $step == $selected_step ]]; then
                    rlAssertGrep $step output
                else
                    rlAssertNotGrep $step output
                fi
            done
        rlPhaseEnd
    done

    rlPhaseStartTest "All steps"
        rlRun "tmt run --all provision -h local | tee output"
        for step in $steps; do
            rlAssertGrep $step output
        done
    rlPhaseEnd

    rlPhaseStartTest "Skip steps"
        rlRun "tmt run --skip prepare | tee output"
        for step in $steps; do
            if [[ $step == prepare ]]; then
                rlAssertNotGrep $step output
            else
                rlAssertGrep $step output
            fi
        done
    rlPhaseEnd

    rlPhaseStartTest "Until"
        rlRun "tmt run --until execute | tee output"
        for step in discover provision prepare execute; do
            rlAssertGrep $step output
        done
        for step in report finish; do
            rlAssertNotGrep $step output
        done
        rlAssertGrep '1 test executed' output
    rlPhaseEnd

    rlPhaseStartTest "Since"
        rlRun "tmt run --last --since report | tee output"
        for step in discover provision prepare execute; do
            rlAssertNotGrep $step output
        done
        for step in report finish; do
            rlAssertGrep $step output
        done
        rlAssertGrep '1 test passed' output
    rlPhaseEnd

    rlPhaseStartTest "Invalid"
        for option in 'since' 'until' 'skip'; do
            rlRun "tmt run --$option invalid 2>&1 | tee output" 2
            rlAssertGrep "Invalid value" output
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -f output" 0 "Removing tmp file"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
