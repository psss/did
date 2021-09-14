#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "set -o pipefail"
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Force the whole run - new workdir"
        # The first run, fresh, no results should be found
        rlRun "tmt run -ddvvi $run discover | tee output" 0 "First run (fresh)"
        rlAssertGrep "Run data not found." output
        rlAssertGrep "Discovered tests not found." output
        rlAssertNotGrep "Discover.*already done" output
        rlAssertNotGrep "Provision.*already done" output
        rlAssertGrep "1 test selected" output
        rlAssertNotGrep "1 guest provisioned" output

        # Discover step done, no other steps executed
        rlRun "tmt run -ddvvi $run | tee output" 0 "Second run (done)"
        rlAssertNotGrep "Run data not found." output
        rlAssertNotGrep "Discovered tests not found." output
        rlAssertGrep "Discover.*already done" output
        rlAssertNotGrep "Provision.*already done" output
        rlAssertGrep "1 test selected" output
        rlAssertNotGrep "1 guest provisioned" output

        # Force, all steps should be executed again
        rlRun "tmt run --scratch -ddvvi $run | tee output" 0 "Third run (force)"
        rlAssertGrep "Run data not found." output
        rlAssertGrep "Discovered tests not found." output
        rlAssertNotGrep "Discover.*already done" output
        rlAssertNotGrep "Provision.*already done" output
        rlAssertGrep "1 test selected" output
        rlAssertGrep "1 guest provisioned" output

        # Finally wake up, everything should be done
        rlRun "tmt run -ddvvi $run | tee output" 0 "Fourth run (wake)"
        rlAssertNotGrep "Run data not found." output
        rlAssertNotGrep "Discovered tests not found." output
        rlAssertGrep "Discover.*already done" output
        rlAssertGrep "Provision.*already done" output
        rlAssertGrep "1 test selected" output
        rlAssertGrep "1 guest provisioned" output
    rlPhaseEnd

    rlPhaseStartTest "Force all steps"
        # The first run, start from scratch, no results should be found
        rlRun "tmt run --scratch -ddvvi $run | tee output" 0 "First run (fresh)"
        rlAssertGrep "Discovered tests not found." output
        rlAssertGrep "1 test selected" output

        new_file="$run/tmpfile"
        rlRun "touch $new_file" 0 "Create a file in the workdir"
        rlAssertExists $new_file

        # Second run, force all enabled steps
        rlRun "tmt run --force -ddvvi $run | tee output" 0 "Second run (force)"
        rlAssertGrep "Discovered tests not found." output
        rlAssertGrep "1 test selected" output
        rlAssertExists $new_file
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -rf output $run" 0 "Remove run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
