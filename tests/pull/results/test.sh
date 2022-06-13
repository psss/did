#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
    rlPhaseEnd

    for method in ${METHODS:-local}; do
        rlPhaseStartTest "Test $method"
            # Run the plan, check for expected results
            rlRun -s "tmt run -av --scratch --id $run provision -h $method" 1
            rlAssertGrep "2 tests passed and 1 test failed" $rlRun_LOG

            # Check output and extra logs in the test data directory
            data="$run/plan/execute/data"
            rlAssertGrep "ok" "$data/test/good/output.txt"
            rlAssertGrep "ko" "$data/test/bad/output.txt"
            rlAssertGrep "extra good" "$data/test/good/data/extra.log"
            rlAssertGrep "extra bad" "$data/test/bad/data/extra.log"

            # Check logs in the plan data directory
            rlAssertGrep "common good" "$run/plan/data/log.txt"
            rlAssertGrep "common bad" "$run/plan/data/log.txt"

            # Check report of the last run for correct results
            rlRun -s "tmt run --last report" 1
            rlAssertGrep "2 tests passed and 1 test failed" $rlRun_LOG

            # Check beakerlib's backup directory pull
            if [[ "$method" =~ local|container ]]; then
                # No pull happened so it shoud be present
                rlAssertExists "$data/test/beakerlib/backup"
                rlAssertExists "$data/test/beakerlib/backup-NS1"
                rlAssertNotEquals "any backup dir is present" "$(eval 'echo $data/test/beakerlib/backup*')" "$data/test/beakerlib/backup*"
            else
                # Should be ignored
                rlAssertNotExists "$data/test/beakerlib/backup"
                rlAssertNotExists "$data/test/beakerlib/backup-NS1"
                rlAssertEquals "no backup dir is present" "$(eval 'echo $data/test/beakerlib/backup*')" "$data/test/beakerlib/backup*"
            fi
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
