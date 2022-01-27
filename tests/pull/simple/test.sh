#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmt directory"
        rlRun "pushd $tmp"
    rlPhaseEnd

    for method in ${METHODS:-local}; do
        rlPhaseStartTest "Test one step ($method)"
            rlRun "tmt run -i $run --scratch provision -h $method finish"
        rlPhaseEnd

        rlPhaseStartTest "Test two steps ($method)"
            rlRun "tmt run -i $run --scratch provision -h $method"
            rlRun "tmt run -i $run finish"
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $run $tmp" 0 "Remove run & tmp directory"
    rlPhaseEnd
rlJournalEnd
