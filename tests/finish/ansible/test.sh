#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    for method in ${METHODS:-container}; do
        rlPhaseStartTest "Test ($method)"
            rlRun "tmt run -arv provision -h $method"

            # For container provision try centos images as well
            if [[ $method == container ]]; then
                rlRun "tmt run -arv finish provision -h $method -i centos:7"
                rlRun "tmt run -arv finish provision -h $method -i centos:8"
            fi

            # After the local provision remove the test file
            if [[ $method == local ]]; then
                rlRun "sudo rm -f /tmp/finished"
            fi
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
