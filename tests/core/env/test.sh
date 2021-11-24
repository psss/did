#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    rlPhaseStartTest "Check the TMT_DEBUG variable"
        rlRun "TMT_DEBUG=3 tmt plan show | tee output"
        rlAssertGrep "Using the 'DiscoverFmf' plugin" 'output'
        rlRun "TMT_DEBUG=weird tmt plan show 2>&1 | tee output" 2
        rlAssertGrep "Invalid debug level" 'output'
    rlPhaseEnd

    for execute in 'shell.detach' 'shell.tmt'; do
        tmt="tmt run -avvvr execute --how $execute"

        rlPhaseStartTest "Variable in L1 ($execute)"
            rlRun "$tmt plan --name no test --name yes | tee output"
            rlAssertGrep '>>>L1<<<' 'output'
        rlPhaseEnd

        rlPhaseStartTest "Variable in L2 ($execute)"
            rlRun "$tmt plan --name yes test --name no | tee output"
            rlAssertGrep '>>>L2<<<' 'output'
            rlRun "$tmt plan --name yes test --name yes | tee output"
            rlAssertGrep '>>>L2<<<' 'output'
        rlPhaseEnd

        rlPhaseStartTest "Variable in option ($execute)"
            for plan in yes no; do
                for test in yes no; do
                    rlRun "tmt run -avvvr -e STR=O -e INT=0 \
                        execute --how $execute \
                        plan --name $plan \
                        test --name $test | tee output"
                    rlAssertGrep '>>>O0<<<' 'output'
                done
            done
        rlPhaseEnd

        # Use the same setup as the test above, but instead of defining
        # variables on the command line read them from a YAML file
        rlPhaseStartTest "Variable in YAML file ($execute)"
            for plan in yes no; do
                for test in yes no; do
                    rlRun "tmt run -avvvr -e @vars.yaml \
                        execute --how $execute \
                        plan --name $plan \
                        test --name $test | tee output"
                    rlAssertGrep '>>>O0<<<' 'output'
                done
            done
        rlPhaseEnd

        rlPhaseStartTest "Empty environment file ($execute)"
            rlRun -s "tmt run -r -e @empty.yaml 2>&1"
            rlAssertGrep "WARNING.*Empty environment file" $rlRun_LOG
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
