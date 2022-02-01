#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
    rlPhaseEnd

    for method in ${METHODS:-container}; do
        rlPhaseStartTest "Test ($method)"
            # Prepare common options, run given method
            tmt="tmt run -i $run --scratch"
            rlRun "$tmt -av provision -h $method"

            # Check that created file is synced back
            rlRun "ls -l $run/plan/data"
            rlAssertExists "$run/plan/data/my_file.txt"

            # For container provision try centos images as well
            if [[ $method == container ]]; then
                rlRun "$tmt -av finish provision -h $method -i centos:7"
                rlRun "$tmt -av finish provision -h $method -i centos:stream8"
            fi

            # After the local provision remove the test file
            if [[ $method == local ]]; then
                rlRun "sudo rm -f /tmp/finished"
            fi
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "rm -r $run" 0 "Removing run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
