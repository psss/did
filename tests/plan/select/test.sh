#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create temporary run workdir"
        rlRun "output=\$(mktemp)" 0 "Create output file"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "tmt plan ls"
        rlRun "tmt plan ls | tee $output"
        rlAssertGrep "/plans/features/core" $output
        rlAssertGrep "/plans/features/basic" $output
    rlPhaseEnd

    rlPhaseStartTest "tmt plan ls <name>"
        rlRun "tmt plan ls core | tee $output"
        rlAssertGrep "/plans/features/core" $output
        rlAssertNotGrep "/plans/features/basic" $output
    rlPhaseEnd

    rlPhaseStartTest "tmt plan ls non-existent"
        rlRun "tmt plan ls non-existent | tee $output"
        rlRun "[[ $(wc -l <$output) == 0 ]]" 0 "Check no output"
    rlPhaseEnd

    for filter in '-f' '--filter'; do
        rlPhaseStartTest "tmt plan show $filter <filter>"
            rlRun "tmt plan show $filter description:.*fast.* | tee $output"
            rlAssertGrep '/plans/features/core' $output
            rlAssertNotGrep '/plans/features/basic' $output
        rlPhaseEnd
    done

    for name in '-n' '--name'; do
        rlPhaseStartTest "tmt run plan $name <name>"
            tmt='tmt run -i $tmp discover'
            rlRun "$tmt plan $name core 2>&1 >/dev/null | tee $output"
            rlAssertGrep "^/plans/features/core" $output
            rlAssertNotGrep "^/plans/features/basic" $output
            rlRun "$tmt plan $name non-existent 2>&1 >/dev/null | tee $output" 2
            rlAssertGrep "No plans found." $output
        rlPhaseEnd
    done

    for exclude in '-x' '--exclude'; do
        rlPhaseStartTest "tmt plan ls $exclude <regex>"
            rlRun "tmt plan ls | tee $output"
            rlAssertGrep "/plans/features/core" $output
            rlRun "tmt plan ls $exclude core | tee $output"
            rlAssertNotGrep "/plans/features/core" $output
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "rm -r $tmp" 0 "Remove temporary run workdir"
        rlRun "rm $output" 0 "Remove output file"
    rlPhaseEnd
rlJournalEnd
