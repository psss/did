#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    for execute in 'shell.detach' 'shell.tmt'; do
        tmt="tmt run -avvv execute --how $execute"

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
                    rlRun "tmt run -avvv -e STR=O -e INT=0 \
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
                    rlRun "tmt run -avvv -e @vars.yaml \
                        execute --how $execute \
                        plan --name $plan \
                        test --name $test | tee output"
                    rlAssertGrep '>>>O0<<<' 'output'
                done
            done
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
