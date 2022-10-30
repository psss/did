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
        rlRun -s "tmt run -ddvvi $run discover" 0 "First run (fresh)"
        rlAssertGrep "Run data not found." $rlRun_LOG
        rlAssertGrep "Discovered tests not found." $rlRun_LOG
        rlAssertNotGrep "Discover.*already done" $rlRun_LOG
        rlAssertNotGrep "Provision.*already done" $rlRun_LOG
        rlAssertGrep "1 test selected" $rlRun_LOG
        rlAssertNotGrep "1 guest provisioned" $rlRun_LOG

        # Discover step done, no other steps executed
        rlRun -s "tmt run -ddvvi $run" 0 "Second run (done)"
        rlAssertNotGrep "Run data not found." $rlRun_LOG
        rlAssertNotGrep "Discovered tests not found." $rlRun_LOG
        rlAssertGrep "Discover.*already done" $rlRun_LOG
        rlAssertNotGrep "Provision.*already done" $rlRun_LOG
        rlAssertGrep "1 test selected" $rlRun_LOG
        rlAssertNotGrep "1 guest provisioned" $rlRun_LOG

        # Force, all steps should be executed again
        rlRun -s "tmt run --scratch -ddvvi $run" 0 "Third run (force)"
        rlAssertGrep "Run data not found." $rlRun_LOG
        rlAssertGrep "Discovered tests not found." $rlRun_LOG
        rlAssertNotGrep "Discover.*already done" $rlRun_LOG
        rlAssertNotGrep "Provision.*already done" $rlRun_LOG
        rlAssertGrep "1 test selected" $rlRun_LOG
        rlAssertGrep "1 guest provisioned" $rlRun_LOG

        # Finally wake up, everything should be done
        rlRun -s "tmt run -ddvvi $run" 0 "Fourth run (wake)"
        rlAssertNotGrep "Run data not found." $rlRun_LOG
        rlAssertNotGrep "Discovered tests not found." $rlRun_LOG
        rlAssertGrep "Discover.*already done" $rlRun_LOG
        rlAssertGrep "Provision.*already done" $rlRun_LOG
        rlAssertGrep "1 test selected" $rlRun_LOG
        rlAssertGrep "1 guest provisioned" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Force all steps"
        # The first run, start from scratch, no results should be found
        rlRun -s "tmt run --scratch -ddvvi $run" 0 "First run (fresh)"
        rlAssertGrep "Discovered tests not found." $rlRun_LOG
        rlAssertGrep "1 test selected" $rlRun_LOG

        new_file="$run/tmpfile"
        rlRun "touch $new_file" 0 "Create a file in the workdir"
        rlAssertExists $new_file

        # Second run, force all enabled steps
        rlRun -s "tmt run --force -ddvvi $run" 0 "Second run (force)"
        rlAssertGrep "Discovered tests not found." $rlRun_LOG
        rlAssertGrep "1 test selected" $rlRun_LOG
        rlAssertExists $new_file
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -rf $run" 0 "Remove run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
