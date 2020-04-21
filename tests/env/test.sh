#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    rlPhaseStartTest 'Variable in L1'
        rlRun "tmt run plan --name no test --name yes | tee output"
        rlAssertGrep '>>>L1<<<' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Variable in L2'
        rlRun "tmt run plan --name yes test --name no | tee output"
        rlAssertGrep '>>>L2<<<' 'output'
        rlRun "tmt run plan --name yes test --name yes | tee output"
        rlAssertGrep '>>>L2<<<' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Variable in option'
        for plan in yes no; do
            for test in yes no; do
                selection="plan --name $plan test --name $test"
                rlRun "tmt run -e TEST=OP $selection | tee output"
                rlAssertGrep '>>>OP<<<' 'output'
            done
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
