#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    for method in ${METHODS:-container}; do
        tmt="tmt run --all --remove provision --how $method"

        # Verify against the default provision image
        rlPhaseStartTest "Test the default image ($method)"
            rlRun "$tmt"
        rlPhaseEnd

        # Check CentOS images for container provision
        if [[ "$method" == "container" ]]; then
            for image in centos:7 centos:stream8; do
                rlPhaseStartTest "Test $image ($method)"
                    rlRun "$tmt --image $image"
                rlPhaseEnd
            done
        fi

        # Add one extra CoreOS run for virtual provision
        if [[ "$method" == "virtual" ]]; then
            rlPhaseStartTest "Test fedora-coreos ($method)"
                rlRun "$tmt --image fedora-coreos"
            rlPhaseEnd
        fi
    done

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
