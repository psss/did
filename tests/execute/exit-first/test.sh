#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    for execute_method in tmt; do
        rlPhaseStartTest "Plan key - $execute_method"
            plan="--scratch -i $run plan -n exit-first"
            rlRun -s "tmt run -a $plan execute -h $execute_method" 1
            # The second test (passing) should not be executed
            rlAssertNotGrep "1 test passed" $rlRun_LOG
            rlAssertGrep "1 test failed" $rlRun_LOG
            rlRun "rm $rlRun_LOG"
        rlPhaseEnd

        rlPhaseStartTest "Option - $execute_method"
            plan="--scratch -i $run plan -n do-not-exit/$execute_method"
            rlRun -s "tmt run -a $plan execute -h $execute_method" 1
            rlAssertGrep "1 test passed and 1 test failed" $rlRun_LOG
            rlRun "rm $rlRun_LOG"

            # As an option of execute
            rlRun -s "tmt run -a $plan execute --exit-first" 1
            rlAssertNotGrep "1 test passed" $rlRun_LOG
            rlAssertGrep "1 test failed" $rlRun_LOG
            rlRun "rm $rlRun_LOG"

            # As an option of execute method
            rlRun -s "tmt run -a $plan execute -h $execute_method -x" 1
            rlAssertNotGrep "1 test passed" $rlRun_LOG
            rlAssertGrep "1 test failed" $rlRun_LOG
            rlRun "rm $rlRun_LOG"
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
