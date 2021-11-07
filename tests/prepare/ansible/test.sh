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
                rlRun "tmt run -arv provision -h $method -i centos:7"
                rlRun "tmt run -arv provision -h $method -i centos:8"
            fi

            # After the local provision remove the test file
            if [[ $method == local ]]; then
                rlRun "sudo rm -f /tmp/prepared"
            fi
        rlPhaseEnd

        rlPhaseStartTest "Ansible ($method) - check extra-args attribute"
            rlRun "tmt run -rddd discover provision -h $method prepare finish \
                | grep \"ansible-playbook\"\
                | tee output"
            rlAssertGrep "-vvv" output
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
