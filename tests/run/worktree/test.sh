#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    for method in ${METHODS:-container}; do
        rlPhaseStartTest "Simple ($method)"
            rlRun "pushd data/simple"
            rlRun "tmt run -ar provision -h $method report -vvv"
            rlRun "popd"
        rlPhaseEnd

        rlPhaseStartTest "Prepare ($method)"
            rlRun "pushd data/prepare"
            rlRun "tmt run -ar provision -h $method report -vvv"
            rlRun "popd"
        rlPhaseEnd

        rlPhaseStartTest "Ansible ($method)"
            rlRun "pushd data/ansible"
            rlRun "tmt run -ar provision -h $method report -vvv"
            rlRun "popd"
        rlPhaseEnd

        rlPhaseStartTest "Verify the TMT_TREE variable ($method)"
            rlRun "pushd data/tree"
            rlRun "tmt run -ar provision -h $method report -vvv"
            rlRun "popd"
        rlPhaseEnd
    done
rlJournalEnd
