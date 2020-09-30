#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "output=\$(mktemp)" 0 "Create output file"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "tmt test ls"
        rlRun "tmt test ls | tee $output"
        rlAssertGrep "/tests/core/docs" $output
        rlAssertGrep "/tests/core/dry" $output
    rlPhaseEnd

    rlPhaseStartTest "tmt test ls <name>"
        rlRun "tmt test ls docs | tee $output"
        rlAssertGrep "/tests/core/docs" $output
        rlAssertNotGrep "/tests/core/dry" $output
    rlPhaseEnd

    rlPhaseStartTest "tmt test ls non-existent"
        rlRun "tmt test ls non-existent | tee $output"
        rlRun "[[ $(wc -l <$output) == 0 ]]" 0 "Check no output"
    rlPhaseEnd

    for filter in '-f' '--filter'; do
        rlPhaseStartTest "tmt test show $filter <filter>"
            rlRun "tmt test show $filter tier:0 | tee $output"
            rlAssertGrep '/tests/core/smoke' $output
            rlAssertNotGrep "/tests/core/docs" $output
        rlPhaseEnd
    done

    for name in '-n' '--name'; do
        rlPhaseStartTest "tmt run test $name <name>"
            tmt='tmt run -r plan --name core discover -v'
            rlRun "$tmt test $name docs | tee $output"
            rlAssertGrep "/tests/core/docs" $output
            rlAssertNotGrep "/tests/core/dry" $output
            rlRun "$tmt test $name non-existent | tee $output"
            rlAssertGrep "No tests found" $output
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "rm $output" 0 "Remove output file"
    rlPhaseEnd
rlJournalEnd
