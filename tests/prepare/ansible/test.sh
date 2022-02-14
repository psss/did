#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    for method in ${METHODS:-container}; do
        for plan in local remote; do
            rlPhaseStartTest "Test $plan playbook ($method)"
                rlRun "tmt run -arv provision -h $method plan -n /$plan"

                # For container provision try centos images as well
                if [[ $method == container ]]; then
                    rlRun "tmt run -arv provision -h $method -i centos:7 plan -n /$plan"
                    rlRun "tmt run -arv provision -h $method -i centos:stream8 plan -n /$plan"
                fi

                # After the local provision remove the test file
                if [[ $method == local ]]; then
                    rlRun "sudo rm -f /tmp/prepared"
                fi
            rlPhaseEnd

            rlPhaseStartTest "Ansible ($method) - check extra-args attribute"
                rlRun "tmt run -rddd discover provision -h $method prepare finish plan -n /$plan \
                    | grep \"ansible-playbook\"\
                    | tee output"
                rlAssertGrep "-vvv" output
            rlPhaseEnd
        done
    done

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
