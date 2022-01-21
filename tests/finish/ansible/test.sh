#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        # Create a temporary directory used for testing
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
    rlPhaseEnd

    for method in ${METHODS:-container}; do
        rlPhaseStartTest "Test ($method)"
            rlRun "tmt run -i $tmp --scratch -av provision -h $method"
            # Check that created file is synced back
            rlRun "ls -l $tmp/plan/tree"
            rlAssertExists "$tmp/plan/tree/my_file.txt"

            # For container provision try centos images as well
            if [[ $method == container ]]; then
                rlRun "tmt run -i $tmp --scratch -av finish provision -h $method -i centos:7"
                rlRun "tmt run -i $tmp --scratch -av finish provision -h $method -i centos:8"
            fi

            # After the local provision remove the test file
            if [[ $method == local ]]; then
                rlRun "sudo rm -f /tmp/finished"
            fi
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
