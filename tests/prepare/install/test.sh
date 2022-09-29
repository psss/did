#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    # Run basic tests against all enabled provision methods
    for method in ${METHODS:-container}; do
        provision="provision --how $method"

        rlPhaseStartTest "Install an existing package ($method)"
            rlRun "tmt run -adddvvvr $provision plan --name existing"
        rlPhaseEnd

        rlPhaseStartTest "Report a missing package ($method)"
            rlRun "tmt run -adddvvvr $provision plan --name missing" 2
        rlPhaseEnd

        # Add one extra CoreOS run for virtual provision
        if [[ "$method" == "virtual" ]]; then
            provision="provision --how $method --image fedora-coreos"

            rlPhaseStartTest "Install an existing package ($method, CoreOS)"
                rlRun "tmt run -adddvvvr $provision plan --name existing"
            rlPhaseEnd

            rlPhaseStartTest "Report a missing package ($method, CoreOS)"
                rlRun "tmt run -adddvvvr $provision plan --name missing" 2
            rlPhaseEnd
        fi
    done

    rlPhaseStartTest "Just enable copr"
        rlRun "tmt run -adddvvvr plan --name copr"
    rlPhaseEnd

    rlPhaseStartTest "Escape package names"
        rlRun "tmt run -adddvvvr plan --name escape"
    rlPhaseEnd

    rlPhaseStartTest "Exclude selected packages"
        rlRun "tmt run -adddvvvr plan --name exclude"
    rlPhaseEnd

    rlPhaseStartTest "Install from epel7 copr"
        rlRun "tmt run -adddvvvr plan --name epel7"
    rlPhaseEnd

    rlPhaseStartTest "Install remote packages"
        rlRun "tmt run -adddvvvr plan --name epel8-remote"
    rlPhaseEnd

    rlPhaseStartTest "Install debuginfo packages"
        rlRun "tmt run -adddvvvr plan --name debuginfo"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
