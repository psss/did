#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

steps='discover provision prepare execute report finish'

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    options='--scratch -i $tmp'
    for selected_step in $steps; do
        rlPhaseStartTest "Select $selected_step"
            exitcode=0
            [[ $selected_step == execute ]] && exitcode=2
            [[ $selected_step == report ]] && exitcode=3
            rlRun "tmt run $options $selected_step 2>&1 >/dev/null | tee output" $exitcode
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
        rlRun "tmt run $options --all provision -h local 2>&1 >/dev/null | tee output"
        for step in $steps; do
            rlAssertGrep $step output
        done
    rlPhaseEnd

    rlPhaseStartTest "Skip steps"
        rlRun "tmt run $options --skip prepare 2>&1 >/dev/null | tee output"
        for step in $steps; do
            if [[ $step == prepare ]]; then
                rlAssertNotGrep $step output
            else
                rlAssertGrep $step output
            fi
        done
    rlPhaseEnd

    rlPhaseStartTest "Until"
        rlRun "tmt run $options --until execute discover -h shell 2>&1 >/dev/null | tee output"
        for step in discover provision prepare execute; do
            rlAssertGrep $step output
        done
        for step in report finish; do
            rlAssertNotGrep $step output
        done
        rlAssertGrep '1 test executed' output
    rlPhaseEnd

    rlPhaseStartTest "Since"
        rlRun "tmt run --last --since report finish -h shell 2>&1 >/dev/null | tee output"
        for step in discover provision prepare execute; do
            rlAssertNotGrep $step output
        done
        for step in report finish; do
            rlAssertGrep $step output
        done
        rlAssertGrep '1 test passed' output
    rlPhaseEnd

    rlPhaseStartTest "Before"
        rlRun "tmt run $options --before report discover -h shell 2>&1 >/dev/null | tee output"
        for step in discover provision prepare execute; do
            rlAssertGrep $step output
        done
        for step in report finish; do
            rlAssertNotGrep $step output
        done
        rlAssertGrep '1 test executed' output
    rlPhaseEnd

    rlPhaseStartTest "After"
        rlRun "tmt run --last --after execute finish -h shell 2>&1 >/dev/null | tee output"
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
            rlRun "tmt run $options --$option invalid 2>&1 >/dev/null | tee output" 2
            rlAssertGrep "Invalid value" output
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -f output" 0 "Removing tmp file"
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
